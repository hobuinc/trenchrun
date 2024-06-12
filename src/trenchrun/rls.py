from . import data
from . import blend
from .logs import logger
import uuid

import numpy as np
import pdal
import requests
import pathlib
import geocoder
import pyproj
from osgeo import gdal

from shapely.geometry import shape, Polygon, LineString
from shapely.ops import transform
from shapely import wkt

def get_polyline(args):

    line_dd = wkt.loads(args.line)
    line_srs = pyproj.CRS("EPSG:4326")
    if args.line_srs:
        line_srs = pyproj.CRS(args.line_srs)

    dsm_srs_wkt = gdal.Open(f'{args.input}').GetSpatialRef().ExportToWkt()
    if not dsm_srs_wkt:
        raise Exception("Input does not have a SRS, we have to stop. Use a VRT to define it or something")
    dsm_srs = pyproj.CRS(dsm_srs_wkt)

    forward = pyproj.Transformer.from_crs(line_srs, dsm_srs, always_xy=True).transform
    reverse = pyproj.Transformer.from_crs(dsm_srs, line_srs, always_xy=True).transform

    line_wm = transform(forward, line_dd)
    poly_wm = line_wm.buffer(2*args.range, cap_style='square')


    poly_dd = transform(reverse, poly_wm)
    return line_dd, line_wm, poly_dd, poly_wm




def do(args):
    logger.info(f"opening {args.input} for processing")


    # python do.py "MULTILINESTRING ((-91.563762 41.649644,-91.5638203 41.6496412,-91.563971 41.649634,-91.564446 41.649632,-91.5648984 41.64963,-91.565474 41.649639,-91.566724 41.649644))"
    line_dd, line_wm, poly_dd, poly_wm = get_polyline(args)

    raster = gdal.Open(f'{args.input}')

    dense = densify(line_wm, 10)
    points = dense.xy

    sheds = []
    for i in range(len(points[0])):

        x0 = points[0][i]
        y0 = points[1][i]

        sheds.append(viewshed(args,raster, x0, y0))


    options = gdal.BuildVRTOptions(resampleAlg='nearest', addAlpha=True,srcNodata=0)
    vrt = gdal.BuildVRT('/vsimem/my.vrt', [r for r in sheds], options=options)
    vrt = None

    driver = gdal.GetDriverByName('GTiff')
    l = gdal.ReadDir('/vsimem/')
    vs = gdal.Open('/vsimem/my.vrt')
    dst_ds = driver.CreateCopy(f'{args.output}', vs, strict=0)


def compute_utmzone(bounds):
    from pyproj import CRS
    from pyproj.aoi import AreaOfInterest
    from pyproj.database import query_utm_crs_info

    utm_crs_list = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(
            west_lon_degree=bounds[0],
            south_lat_degree=bounds[1],
            east_lon_degree=bounds[2],
            north_lat_degree=bounds[3],
        ),
    )
    utm_crs = CRS.from_epsg(utm_crs_list[0].code)
    return utm_crs


def densify(line_geometry, step):
    length_m = line_geometry.length  # get the length
    xy = []  # to store new tuples of coordinates

    for distance_along_old_line in np.arange(0, int(length_m), step):
        point = line_geometry.interpolate(
            distance_along_old_line
        )  # interpolate a point every step along the old line
        xp, yp = point.x, point.y  # extract the coordinates

        xy.append((xp, yp))  # and store them in xy list

    new_line = LineString(
        xy
    )  # Here, we finally create a new line with densified points.

    return new_line


def warp(raster_filename, outSrs, inSrs=None):
    pass


def viewshed(args, raster_ds, x, y, rng=500):

    band = raster_ds.GetRasterBand(1)
    filename = f'/vsimem/{uuid.uuid4()}.tif'
    ds = gdal.ViewshedGenerate(
        raster_ds.GetRasterBand(1),
        "GTiff",
        filename,
        ["INTERLEAVE=BAND"],
        x,
        y,
        1.5,
        args.height,  # targetHeight
        255,  # visibleVal
        0,  # invisibleVal
        0,  # outOfRangeVal
        -1.0,  # noDataVal,
        0.85714,  # dfCurvCoeff
        gdal.GVM_Edge,
        rng,  # maxDistance
        heightMode=gdal.GVOT_NORMAL,
        options=["UNUSED=YES"],
    )

    del ds

    return filename

