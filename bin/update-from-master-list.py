#!/usr/bin/env python3
import argparse
import json

import urllib.request

from pathlib import Path


THIS = Path(__file__).resolve()
REF_DIR = THIS.parent.parent.joinpath('reference')

URL = r'https://opendata.arcgis.com/api/v3/datasets/db1a263c413542deb41869e4ed2ba376_0/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1'

EXCLUDED_PROPERTIES = set([
    'agol_report_url',
    'OBJECTID',
    'latitude',
    'longitude',
    'stationtriplet',
])


def get_pourpoints(url):
    with urllib.request.urlopen(url) as response:
        return json.load(response)['features']


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


def fix_properties(feature):
    props = feature['properties']

    props['awdb_id'] = props['awdb_id'].replace('"', '')
    props['aoi_exist'] = None if props['aoi_exist'] == -99 else bool(props['aoi_exist'])
    props['forecastpoint'] = bool(props['forecastpoint'])
    props['active'] = bool(props['active'])

    if props['basinarea'] == 0:
        props['basinarea'] = None

    for prop in EXCLUDED_PROPERTIES:
        del props[prop]

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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-u',
        '--url',
        help='Url of the master feature list geojson',
        default=URL,
    )
    parser.add_argument(
        '-d',
        '--reference-dir',
        help='Path of the reference pourpoint directory',
        default=REF_DIR,
    )
    return parser.parse_args()


def main():
    args = parse_args()
    process_pourpoints(get_pourpoints(args.url), args.reference_dir)


if __name__ == '__main__':
    main()
