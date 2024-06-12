
from .logs import logger

import pyproj
from shapely.geometry import shape, Polygon, LineString
from shapely.ops import transform
import pdal

import json
import math

def make_pipeline(args):
    ept = pdal.Reader.ept(filename=args.ept, polygon = args.geometry.wkt, requests=16)
    withheld = pdal.Filter.expression(expression="Withheld != 1")
    no_noise = pdal.Filter.expression(expression = "!(Classification == 12 || Classification ==7)")
    gdal = pdal.Writer.gdal(filename='dsm.tif', bounds = str(list(args.geometry.bounds)),
                            data_type = "float32",
                            dimension = "Z",
                            output_type="idw",
                            window_size=3,
                            resolution = 0.5)
    args.pipeline = ept | withheld | no_noise | gdal

def reproject_geojson(args):
    geojson_srs = pyproj.CRS("EPSG:4326")
    ept_srs = pyproj.CRS("EPSG:3857")

    geojson = args.geojson.open().read()
    geojson = json.loads(geojson)
    if 'features' in geojson:
        geometry = geojson['features'][0]['geometry']
    else:
        geometry = geojson['geometry']
    geojson = shape(geometry)

    forward = pyproj.Transformer.from_crs(geojson_srs, ept_srs, always_xy=True).transform

    geometry = transform(forward, geojson)
    if (not math.isnan(args.buffer)):
        geometry = geometry.buffer(args.buffer)
    args.geometry = geometry

def do(args):
    logger.info(f"opening {args.ept} for processing")

    reproject_geojson(args)
    make_pipeline(args)
    with args.output.open(mode='w') as f:
        f.write(args.pipeline.pipeline)


