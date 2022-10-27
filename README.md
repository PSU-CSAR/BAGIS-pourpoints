# BAGIS Pourpoints

This repository contains the reference files for all the BAGIS pourpoint
basins. Each file is a geojson representation of a BAGIS pourpoint object,
with a point geometery and, optionally, a basin polyon.

The files have two formats:

* Point only:

  ```
  {
    "type": "Feature",
    "id": "008NG005:BC:USGS",
    "geometry" : {
      "type": "Point",
      "coordinates": [-115.416645907612,49.4166535142733]
    },
    "properties": {
      "name": "Kootenay River at Wardner",
      "source": "ref",
    }
  }
  ```

* Point with basin polygon:

  ```
  {
    "type": "GeometryCollection",
    "id": "10336715:NV:USGS",
    "geometries": [
      {
        "type": "Point",
	"coordinates": [-119.9079470066,39.1721247477916]
      },
      {
        "type": "MultiPolygon",
	"coordinates": [[[[-119.89934048816,39.1540244499329],...]]]
      }
    ],
    "properties": {
      "name": "Marlette Lake Inflow",
      "source" : "ref"
    }
  }
  ```

Note that both `Polygon` or `MultiPolygon` types are supported for basin area
geometries.


## How to use this repo

These files are intended to be used to seed CSAR BAGIS web project databases
with the reference and user pourpoint records. For loading/updating a given
project database with these fixtures, please consult that project's documentation.

### Adding a new reference record

Records are easily exported from the BAGIS plugin, where applicable. Records
can also be generated manually or with other tooling where required, simply
follow the formatting detailed above.

Reference pourpoint records should have a `source` of `ref` and need to be
named with their `stationtriplet` with the `:` characters converted to `_` and
the extension `.geojson`.  For example, `06034700_MT_USGS.geojson`.

For new reference records place the geojson file in the `reference` directory.

Reference pourpoints need to be updated with the master list properies. After
adding new records, run the script `bin/update-from-master-list.py`, which will
pull the master list and iterate through all the reference pourpoint files,
updating them with the master list properties. Note that the geometries will
not be updated from the master list.

Review all changes from the update script via `git diff` to ensure nothing
unexpected has happened.

### New point-only record from master list

When running the update script, any new points on the master list will be added
to the reference set with a `source` of `ref`.

### Updating an existing record with a geometry

Simply overwrite the existing file per the "Adding a new record" above. If the
new record does not have all the properties from the master list, the update
from the master list will resolve that.

### User pourpoints

For pourpoints added by user request that do not match stations in the master
list, add them to the `user` directory. Ensure the file extension is `.geojson`
and use the same format as detailed above. For the `source` property use
`user`.


## Pourpoint? A note on terminology

In fact, the terminology used for naming this repo is not really correct. It
turns out we have two types of points:

* Pourpoint: the point through which BAGIS has calculated all basin outflow
  will pass
* Forecast point: the reference location of the station providing ground truth
  (typically a USGS streamflow gauge)

In theory these points will coincide in the same location. In practice, they
tend to have some differences.  Forecast point coordinates are rarely, if ever,
located directly on the stream feature which they are to be measuing.  This can
be due to a number of factors, such as inaccurate coordinates or wide water
bodies.  The BAGIS tools snap the forecase point to the stream before
calculating the basin, which gives the pourpoint.

The points in these files are mostly, if not completely, forecast points. The
intended use-case at current for these files is cartographic, so the forecast
point vs pourpoint difference is not particularly meaningful. As a result we
have not attempted to reconcile that difference at this time.
