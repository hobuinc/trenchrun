
import matplotlib as mpl
import matplotlib.pylab as plt
import uuid
from . import logs

import trenchrun

import numpy as np
import numpy.ma as ma
from osgeo import gdal
gdal.UseExceptions()

from .data import Intensity, DSM, Daylight


def readBand(filename,
             bandNumber,
             npDataType = np.float32,
             normalize = False):

    ds = gdal.Open(filename)
    band = ds.GetRasterBand(bandNumber)
    projection = ds.GetProjection()
    array = band.ReadAsArray().astype(npDataType)
    if normalize:
        norm = mpl.colors.Normalize()
        med = np.median(array)
        std = np.std(array)
        factor = 3
        min = med - factor*std
        max = med + factor*std
        norm = mpl.colors.Normalize(vmin=min, vmax=max, clip=True)
        array = norm(array)

    # mask off any nodata values
    nodata = band.GetNoDataValue()
    logs.logger.info(f'nodata value: {nodata} for resource {filename}')
    nans = np.count_nonzero(array == nodata)
    array[array==nodata] = np.nan
    array = np.ma.array (array, mask=np.isnan(array))
    return array

def getInfo(filename):
    output = {}
    ds = gdal.Open(filename)
    projection = ds.GetProjection()
    output['projection'] = ds.GetProjection()
    output['metadata'] = ds.GetMetadata()
    output['transform'] = ds.GetGeoTransform()
    return output

class Blend(object):
    def __init__(self, intensity: Intensity, dsm: DSM, daylight: Daylight):
        self.intensity = intensity
        self.daylight = daylight
        self.dsm = dsm

    def write(self, args):
        intensityFilename = str(self.intensity.path)
        daylightFilename = str(self.daylight.path)
        intensity = readBand(intensityFilename, 1, np.float32, True)
        daylight = readBand(daylightFilename, 1)
        dsm = readBand(str(self.dsm.path), 1)

        if intensity.shape != daylight.shape:
            raise Exception("Images are not the same size and shape!")

        logs.logger.info(f'Intensity shape {intensity.shape} ')
        logs.logger.info(f'Daylight shape {daylight.shape} ')

        intensity_mask = ma.getmask(intensity)
        daylight_mask = ma.getmask(daylight)
        if args.blue:
            cmap = mpl.cm.Blues_r
        else:
            cmap = mpl.cm.Greys_r

        intensity_RGBA = cmap(intensity)
        intensity_RGBA[...,3] = np.full(intensity.shape, args.alpha)

        cmap = mpl.cm.Greys_r
        daylight_RGB = cmap(daylight)

        RGBA = intensity_RGBA * 0.5 + daylight_RGB * 0.5

        numBands = RGBA.shape[2]

        nodata = np.uint8(255)
        big = (RGBA*255).astype(np.uint8)
        for i in range(numBands):
            ma.putmask(big[...,i], intensity_mask, nodata)
            ma.putmask(big[...,i], daylight_mask, nodata)

        tifpath = f"/vsimem/{str(uuid.uuid4())}.tif"
        gtif = gdal.GetDriverByName("GTiff")
        rast = gtif.Create(tifpath, intensity.shape[1], intensity.shape[0], numBands, gdal.GDT_Byte)

        info = getInfo(intensityFilename)

        rast.SetProjection(info['projection'])
        rast.SetGeoTransform(info['transform'])

        for b in range(numBands):
            band =rast.GetRasterBand(b+1)
            band.WriteArray(big[...,b])
            band.SetNoDataValue(int(nodata))

        png = gdal.GetDriverByName("PNG")

        description='daylight exposure mixed with lidar intensity'
        title = 'Absorptive Daylight Exposure'

        if args.full_output:
            output = str(args.output_path / f"{args.output}-trenchrun.png")
            png.CreateCopy( output, rast, 0,
                [ f'TITLE={title}', f'COMMENT={description}' ] )

        output = str(args.output_path / f"{args.output}-trenchrun.tif")
        logs.logger.info(f'writing trenchrun to {output}')
        ds = gtif.CreateCopy( output, rast, 0,
            [ 'COMPRESS=Deflate', 'TILED=YES','PREDICTOR=2' ] )

        if 'AREA_OR_POINT' in info['metadata']:
            ds.SetMetadataItem('AREA_OR_POINT', info['metadata']['AREA_OR_POINT'])

        ds.SetMetadataItem('TIFFTAG_SOFTWARE',f'Trenchrun {trenchrun.__version__}')
        ds.SetMetadataItem('TIFFTAG_IMAGEDESCRIPTION',f'{description}')
        ds.SetMetadataItem('TIFFTAG_DOCUMENTNAME',f'{title}')

        if args.full_output:
            ao = gdal.Open(str(self.daylight.path))
            output = str(args.output_path / f"{args.output}-occlusion.tif")
            logs.logger.info(f'writing ambient occlusion to {output}')
            ds = gtif.CreateCopy( output, ao, 0,
                [ 'COMPRESS=Deflate', 'TILED=YES','PREDICTOR=2' ] )

            ao = gdal.Open(str(self.dsm.path))
            output = str(args.output_path / f"{args.output}-dsm.tif")
            logs.logger.info(f'writing dsm to {output}')
            ds = gtif.CreateCopy( output, ao, 0,
                [ 'COMPRESS=LZW', 'TILED=YES','PREDICTOR=3' ] )

            ao = gdal.Open(str(self.intensity.path))
            output = str(args.output_path / f"{args.output}-intensity.tif")
            logs.logger.info(f'writing intensity to {output}')
            ds = gtif.CreateCopy( output, ao, 0,
                [ 'COMPRESS=LZW', 'TILED=YES','PREDICTOR=2' ] )
