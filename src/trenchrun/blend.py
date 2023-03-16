
import matplotlib as mpl
import matplotlib.pylab as plt
import uuid
from . import logs

import trenchrun

import numpy as np
import numpy.ma as ma
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
    def __init__(self, data):
        self.data = data

    def do(self):
        intensityFilename = str(self.data.args.intensityPath)
        daylightFilename = str(self.data.args.aoPath)
        intensity = readBand(intensityFilename, 1, np.float32, True)
        daylight = readBand(daylightFilename, 1)

        logs.logger.info(f'Intensity shape {intensity.shape} ')
        logs.logger.info(f'Daylight shape {intensity.shape} ')

        intensity_mask = ma.getmask(intensity)
        daylight_mask = ma.getmask(daylight)
        if self.data.args.blue:
            cmap = mpl.cm.Blues_r
        else:
            cmap = mpl.cm.Greys_r

        intensity_RGBA = cmap(intensity)
        intensity_RGBA[...,3] = np.full(intensity.shape, self.data.args.alpha)

        cmap = mpl.cm.Greys_r
        daylight_RGB = cmap(daylight)

        RGBA = intensity_RGBA * 0.5 + daylight_RGB * 0.5

        numBands = RGBA.shape[2]


        nodata = 255
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
            band.SetNoDataValue(nodata)

        png = gdal.GetDriverByName("PNG")

        description='daylight exposure mixed with lidar intensity'
        title = 'Absorptive Daylight Exposure'

        if self.data.args.full_output:
            png.CreateCopy( f"{self.data.args.output}-trenchrun.png", rast, 0,
                [ f'TITLE={title}', f'COMMENT={description}' ] )

        ds = gtif.CreateCopy( f"{self.data.args.output}-trenchrun.tif", rast, 0,
            [ 'COMPRESS=Deflate', 'TILED=YES','PREDICTOR=2' ] )

        if 'AREA_OR_POINT' in info['metadata']:
            ds.SetMetadataItem('AREA_OR_POINT', info['metadata']['AREA_OR_POINT'])

        ds.SetMetadataItem('TIFFTAG_SOFTWARE',f'Trenchrun {trenchrun.__version__}')
        ds.SetMetadataItem('TIFFTAG_IMAGEDESCRIPTION',f'{description}')
        ds.SetMetadataItem('TIFFTAG_DOCUMENTNAME',f'{title}')

        if self.data.args.full_output:
            ao = gdal.Open(str(self.data.args.aoPath))
            ds = gtif.CreateCopy( f"{self.data.args.output}-occlusion.tif", ao, 0,
                [ 'COMPRESS=Deflate', 'TILED=YES','PREDICTOR=2' ] )

            ao = gdal.Open(str(self.data.args.dsmPath))
            ds = gtif.CreateCopy( f"{self.data.args.output}-dsm.tif", ao, 0,
                [ 'COMPRESS=LZW', 'TILED=YES','PREDICTOR=3' ] )

            ao = gdal.Open(str(self.data.args.intensityPath))
            ds = gtif.CreateCopy( f"{self.data.args.output}-intensity.tif", ao, 0,
                [ 'COMPRESS=LZW', 'TILED=YES','PREDICTOR=2' ] )
