#!/usr/bin/env python3
import argparse
import datetime
import json

import urllib.request

from pathlib import Path


THIS = Path(__file__).resolve()
REF_DIR = THIS.parent.parent.joinpath('reference')
UNMATCHED_DIR = THIS.parent.parent.joinpath('unmatched')

# All three feeds are ArcGIS feature services under the same org. To turn a
# service description URL (.../<service>/FeatureServer) into a geojson feed,
# append the layer id and a query: /0/query?where=1=1&outFields=*&f=geojson

# Base pourpoint list: drives which records exist and their properties.
URL = (
    r'https://services.arcgis.com/SXbDpmb7xQkk44JV/arcgis/rest/services/'
    r'master_aoi_list_fs/FeatureServer/0/query'
    r'?where=1%3D1&outFields=*&returnGeometry=true&f=geojson'
)

# Active forecast stations: source of truth for point locations. Its geometry
# overwrites the coordinates of matching pourpoints; stations absent from the
# base list are added as new reference records from this feed's properties.
LOCATION_URL = (
    r'https://services.arcgis.com/SXbDpmb7xQkk44JV/arcgis/rest/services/'
    r'stations_FCST_ACTIVE/FeatureServer/0/query'
    r'?where=1%3D1&outFields=*&returnGeometry=true&f=geojson'
)

# Basin polygons for the (subset of) points with a delineated AOI.
POLYGON_URL = (
    r'https://services.arcgis.com/SXbDpmb7xQkk44JV/arcgis/rest/services/'
    r'master_FCST_AOI_polygons/FeatureServer/0/query'
    r'?where=1%3D1&outFields=*&returnGeometry=true&f=geojson'
)

EXCLUDED_PROPERTIES = set([
    'agol_report_url',
    'OBJECTID',
    'latitude',
    'longitude',
    'stationtriplet',
    # Present on the feature service but not the historical opendata export;
    # excluded to keep the reference property set unchanged.
    'hasReport',
    'nrcs_report_url',
    'huc2',
    'huc2region',
    'huc2code',
])

# Internal/derived fields we don't want to persist on unmatched polygon records.
POLYGON_EXCLUDED_PROPERTIES = set([
    'OBJECTID',
    'Shape__Area',
    'Shape__Length',
])


def get_features(url, page_size=1000):
    # Feature services cap each response at maxRecordCount, so page through
    # with resultOffset until the service stops flagging exceededTransferLimit.
    features = []
    offset = 0
    while True:
        paged = f'{url}&resultOffset={offset}&resultRecordCount={page_size}'
        with urllib.request.urlopen(paged) as response:
            data = json.load(response)
        batch = data['features']
        features.extend(batch)
        if not data.get('properties', {}).get('exceededTransferLimit'):
            break
        offset += len(batch)
    return features


def get_reference(feature_id, reference_dir):
    reference = reference_dir.joinpath(
        feature_id.replace(':', '_') + '.geojson',
    )
    try:
        ref_feature = json.loads(reference.read_text())
    except FileNotFoundError:
        ref_feature = None

    return reference, ref_feature


def write_reference(ref_file, feature):
    ref_file.write_text(json.dumps(feature, indent=2) + '\n')


def ms_to_iso(ms):
    if ms is None:
        return None
    return datetime.datetime.fromtimestamp(
        ms / 1000,
        tz=datetime.timezone.utc,
    ).strftime('%Y-%m-%dT%H:%M:%SZ')


def ms_to_mdy(ms):
    if ms is None:
        return None
    dt = datetime.datetime.fromtimestamp(ms / 1000, tz=datetime.timezone.utc)
    return f'{dt.month}/{dt.day}/{dt.year}'


def fix_properties(feature):
    props = feature['properties']

    props['awdb_id'] = props['awdb_id'].replace('"', '')
    props['aoi_exist'] = None if props['aoi_exist'] == -99 else bool(props['aoi_exist'])
    props['forecastpoint'] = bool(props['forecastpoint'])
    props['active'] = bool(props['active'])
    # The service returns date fields as epoch milliseconds; the opendata
    # export (and existing files) use an ISO string.
    props['enddate'] = ms_to_iso(props['enddate'])

    if props['basinarea'] == 0:
        props['basinarea'] = None

    for prop in EXCLUDED_PROPERTIES:
        props.pop(prop, None)

    return feature


def process_pourpoint(feature, reference_dir):
    feature['id'] = feature_id = feature['properties']['stationtriplet']
    feature = fix_properties(feature)

    ref_file, ref_feature = get_reference(feature_id, reference_dir)

    if ref_feature is not None:
        print(f'Processing {feature_id} (UPDATE)...')
        for prop, val in feature['properties'].items():
            ref_feature['properties'][prop] = val
    else:
        print(f'Processing {feature_id} (ADD)...')
        ref_feature = feature
        ref_feature['properties']['source'] = 'ref'

    write_reference(ref_file, ref_feature)


def process_pourpoints(features, reference_dir):
    for feature in features:
        process_pourpoint(feature, reference_dir)


def get_point_geometry(ref_feature):
    if ref_feature['type'] == 'GeometryCollection':
        for geom in ref_feature['geometries']:
            if geom['type'] == 'Point':
                return geom
        raise ValueError(
            f"Reference {ref_feature.get('id')} has no Point geometry",
        )
    return ref_feature['geometry']


def set_point_geometry(ref_feature, point_geom):
    if ref_feature['type'] == 'GeometryCollection':
        for i, geom in enumerate(ref_feature['geometries']):
            if geom['type'] == 'Point':
                ref_feature['geometries'][i] = point_geom
                return ref_feature
        raise ValueError(
            f"Reference {ref_feature.get('id')} has no Point geometry",
        )
    ref_feature['geometry'] = point_geom
    return ref_feature


def build_from_location(feature):
    # Stations present in the active-stations service but not the base list only
    # have this feed's (narrower) schema, so map what overlaps and leave the
    # base-only fields null for later completion.
    src = feature['properties']
    elev = src.get('elevation')
    if isinstance(elev, float) and elev.is_integer():
        elev = int(elev)
    return {
        'type': 'Feature',
        'id': src['stationTriplet'],
        'geometry': feature['geometry'],
        'properties': {
            'name': src.get('name'),
            'source': 'ref',
            'begindate': ms_to_mdy(src.get('beginDate')),
            'countyname': src.get('countyName'),
            'enddate': ms_to_iso(src.get('endDate')),
            'active': None,
            'huc': int(src['huc']) if src.get('huc') else None,
            'winter_start_month': src.get('winter_start_month'),
            'winter_end_month': src.get('winter_end_month'),
            'nwccname': None,
            'elevation': None if elev is None else str(elev),
            'basinarea': None,
            'awdb_id': None,
            'usgs_id': None,
            'usgsname': None,
            'forecastpoint': None,
            'bagis_aoiname': None,
            'aoi_exist': None,
        },
    }


def process_location(feature, reference_dir):
    triplet = feature['properties']['stationTriplet']
    ref_file, ref_feature = get_reference(triplet, reference_dir)

    if ref_feature is None:
        print(f'Processing {triplet} (LOCATION ADD)...')
        write_reference(ref_file, build_from_location(feature))
        return

    print(f'Processing {triplet} (LOCATION)...')
    write_reference(
        ref_file,
        set_point_geometry(ref_feature, feature['geometry']),
    )


def process_locations(features, reference_dir):
    for feature in features:
        process_location(feature, reference_dir)


def enrich_with_polygon(ref_feature, polygon_geom):
    # Rebuild as a GeometryCollection of the existing point plus the polygon,
    # replacing any polygon that was already present (the service is master).
    point = get_point_geometry(ref_feature)
    ref_feature['type'] = 'GeometryCollection'
    ref_feature.pop('geometry', None)
    ref_feature['geometries'] = [point, polygon_geom]
    return ref_feature


def build_unmatched(feature):
    feature['id'] = feature['properties']['stationTriplet']
    for prop in POLYGON_EXCLUDED_PROPERTIES:
        feature['properties'].pop(prop, None)
    feature['properties']['source'] = 'unmatched'
    return feature


def process_polygon(feature, reference_dir, unmatched_dir):
    triplet = feature['properties']['stationTriplet']
    ref_file, ref_feature = get_reference(triplet, reference_dir)

    if ref_feature is not None:
        print(f'Processing {triplet} (POLYGON)...')
        write_reference(
            ref_file,
            enrich_with_polygon(ref_feature, feature['geometry']),
        )
    else:
        print(f'Processing {triplet} (UNMATCHED)...')
        unmatched_dir.mkdir(parents=True, exist_ok=True)
        unmatched_file, _ = get_reference(triplet, unmatched_dir)
        write_reference(unmatched_file, build_unmatched(feature))


def process_polygons(features, reference_dir, unmatched_dir):
    for feature in features:
        process_polygon(feature, reference_dir, unmatched_dir)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-u',
        '--url',
        help='Url of the base feature list geojson',
        default=URL,
    )
    parser.add_argument(
        '-l',
        '--location-url',
        help='Url of the active stations geojson (point location source)',
        default=LOCATION_URL,
    )
    parser.add_argument(
        '-p',
        '--polygon-url',
        help='Url of the basin polygon feature service geojson query',
        default=POLYGON_URL,
    )
    parser.add_argument(
        '-d',
        '--reference-dir',
        help='Path of the reference pourpoint directory',
        type=Path,
        default=REF_DIR,
    )
    parser.add_argument(
        '-m',
        '--unmatched-dir',
        help='Path for polygons with no matching pourpoint (for review)',
        type=Path,
        default=UNMATCHED_DIR,
    )
    return parser.parse_args()


def main():
    args = parse_args()
    process_pourpoints(get_features(args.url), args.reference_dir)
    process_locations(get_features(args.location_url), args.reference_dir)
    process_polygons(
        get_features(args.polygon_url),
        args.reference_dir,
        args.unmatched_dir,
    )


if __name__ == '__main__':
    main()
