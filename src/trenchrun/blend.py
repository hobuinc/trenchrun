
import matplotlib as mpl
import matplotlib.pylab as plt
import uuid
from . import logs

__version__= '0.0.1'

import numpy as np
import sys
from osgeo import gdal
gdal.UseExceptions()


def readBand(filename,
             bandNumber,
             npDataType = np.float32,
             normalize = False):

    ds = gdal.Open(filename)
    band = ds.GetRasterBand(bandNumber)
    projection = ds.GetProjection()
    array = band.ReadAsArray().astype(npDataType)
    if normalize:
        array = (array - array.min()) / (array.max() - array.min())

    # mask off any nodata values
    array[array==band.GetNoDataValue()] = np.nan
    return array

def getInfo(filename):
    output = {}
    ds = gdal.Open(filename)
    projection = ds.GetProjection()
    output['projection'] = ds.GetProjection()
    output['metadata'] = ds.GetMetadata()
    return output
    ds.GetMetadata()
    return projection

class Blend(object):
    def __init__(self, data):
        self.data = data

    def do(self):
        intensityFilename = self.data.args.intensityPath
        daylightFilename = self.data.args.aoPath
        intensity = readBand(intensityFilename, 1, np.float32, True)
        daylight = readBand(daylightFilename, 1)

        logs.logger.info(f'Intensity shape {intensity.shape} ')
        logs.logger.info(f'Daylight shape {intensity.shape} ')

        if self.data.args.blue:
            intensity_RGBA = mpl.cm.Blues_r(intensity)
        else:
            intensity_RGBA = mpl.cm.Greys_r(intensity)

        intensity_RGBA[...,3] = np.full(intensity.shape, self.data.args.alpha)

        daylight_RGB = mpl.cm.Greys_r(daylight)

        RGBA = intensity_RGBA * 0.5 + daylight_RGB * 0.5

        numBands = RGBA.shape[2]

        big = (RGBA*255).astype(np.uint8)
        logs.logger.info(f'RGBA shape {big.shape} ')

        tifpath = f"/vsimem/{str(uuid.uuid4())}.tif"
        gtif = gdal.GetDriverByName("GTiff")
        rast = gtif.Create(tifpath, intensity.shape[1], intensity.shape[0], numBands, gdal.GDT_Byte)

        info = getInfo(intensityFilename)

        rast.SetProjection(info['projection'])

        for b in range(numBands):
            rast.GetRasterBand(b+1).WriteArray(big[...,b])

        png = gdal.GetDriverByName("PNG")

        description='daylight exposure mixed with lidar intensity'
        title = 'Absorptive Daylight Exposure'
        png.CreateCopy( f"{self.data.args.output}.png", rast, 0,
            [ f'TITLE={title}', f'COMMENT={description}' ] )

        ds = gtif.CreateCopy( f"{self.data.args.output}.tif", rast, 0,
            [ 'COMPRESS=Deflate', 'TILED=YES','PREDICTOR=2' ] )


        if 'AREA_OR_POINT' in info['metadata']:
            ds.SetMetadataItem('AREA_OR_POINT', info['metadata']['AREA_OR_POINT'])

        ds.SetMetadataItem('TIFFTAG_SOFTWARE',f'Landrush exposure.py {__version__}')
        ds.SetMetadataItem('TIFFTAG_IMAGEDESCRIPTION',f'{description}')
        ds.SetMetadataItem('TIFFTAG_DOCUMENTNAME',f'{title}')

        ao = gdal.Open(self.data.args.aoPath)
        ds = gtif.CreateCopy( f"{self.data.args.output}-occlusion.tif", ao, 0,
            [ 'COMPRESS=Deflate', 'TILED=YES','PREDICTOR=2' ] )

