# BAGIS Pourpoints

This repository contains the reference files for all the BAGIS pourpoint basins.
Each file is a geojson representation of a BAGIS pourpoint object, with a point
geometery and, optionally, a basin polyon.

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

Note that both `Polygon` or `MultiPolygon` types are supported for basin area geometries.
