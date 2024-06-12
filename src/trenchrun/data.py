from . import logs

import json
import tempfile
import subprocess
import shlex
import pathlib

import pdal
from osgeo import gdal


def run(command):
    args = shlex.split(command)
    p = subprocess.Popen(args,
                            stdin = subprocess.PIPE,
                            stdout = subprocess.PIPE,
                            stderr = subprocess.PIPE,)
    ret = p.communicate()

    if p.returncode != 0:
        error = ret[1].decode('utf-8','replace')
        raise RuntimeError(error)

    response = ret[0].decode('utf-8','replace')
    return response

class Product(object):
    def __init__(self, reader):
        self.reader = reader
        self.path = pathlib.Path(tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name)
        self.validate()


    def __del__(self):
        self.path.unlink()

    def getMetadata(self):
        pass

    def getStage(self):
        pass

    def validate(self):
        pass

    def process(self, *args, **kwargs):
        stage = self.getStage()

        pipeline = self.reader.get() | stage

        count = 0
        if pipeline.streamable:
            count = pipeline.execute_streaming(chunk_size=self.reader.args.chunk_size)
        else:
            count = pipeline.execute()

        logs.logger.info(f'Wrote {self.name} product for {count} points')
        self.metadata = pipeline.metadata
        self.getMetadata()


class Intensity(Product):
    def __init__(self, reader):
        self.name = 'Intensity'
        super().__init__(reader)


    def getStage(self):
        stage = pdal.Writer.gdal(
            filename=str(self.path),
            data_type='uint16_t',
            dimension='Intensity',
            output_type = 'idw',
            origin_x = self.reader.args.origin_x,
            origin_y = self.reader.args.origin_y,
            width = self.reader.args.width,
            height = self.reader.args.height,
            resolution=self.reader.args.resolution,
        )

        return stage

    def validate(self):
        qi = self.reader.get().quickinfo
        for key in qi:
            dimensions = [i.strip() for i in qi[key]['dimensions'].split(',')]
            if self.name not in dimensions:
                raise RuntimeError(f"{self.name} information not available, this tool cannot run")


class DSM(Product):
    def __init__(self, reader):
        self.name = 'DSM'
        super().__init__(reader)


    def getStage(self):
        stage = pdal.Writer.gdal(filename=str(self.path),
                                 data_type='float',
                                 dimension='Z',
                                 output_type = 'idw',
                                 resolution=self.reader.args.resolution)
        return stage

    def getMetadata(self):
        ds = gdal.Open(self.path)
        xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
        width, height = ds.RasterXSize, ds.RasterYSize
        # xmax = xmin + width * xpixel
        ymin = ymax + height * ypixel

        self.reader.args.origin_x = xmin
        self.reader.args.origin_y = ymin
        self.reader.args.width = width
        self.reader.args.height = height



class Daylight(object):
    def __init__(self, dsm: DSM):
        self.name = 'Daylight'
        self.path = pathlib.Path(tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name)
        self.dsm = dsm

    def getImageCenter(self):
        # Run our pipeline

        command = f'gdalinfo -json {self.dsm.path}'
        response = run(command)
        j = json.loads(response)
        corner = j['wgs84Extent']['coordinates'][0][0]
        logs.logger.info(f'Fetched image center {corner}')
        return corner


    def process(self):

        lng, lat = self.getImageCenter()

        command = f"""whitebox_tools -r=TimeInDaylight  \
        -i {self.dsm.path} -o {self.path}  --az_fraction=15.0 \
        --max_dist=100.0 --lat={lat:.5f} --long={lng:.5f} """
        logs.logger.info(f"Processing ambient occlusion '{command}'")
        response = run(command)
        logs.logger.info(f"Processed ambient occlusion ")


class Reader(object):
    def __init__(self, args ):
        self.args = args
        self.name = 'Reader'

        self.reader_args = []
        if 'reader_args' in self.args:
            with open(self.args.reader_args,'r') as f:
                self.reader_args = json.loads(f.read())

        if '.json' in self.args.input.suffixes:
            self.inputType = 'pipeline'
        else:
            self.inputType = 'readable'

    def get(self):
        if self.inputType == 'pipeline':
            reader = self.readPipeline()
        else:
            reader = self.readFile()

        return reader
    def readFile(self):
        reader = pdal.Reader(str(self.args.input), *self.reader_args)
        pipeline = reader.pipeline()
        return pipeline

    def readPipeline(self):
        if self.inputType != 'pipeline':
            raise RuntimeError("Data type is not pipeline!")
        j = self.args.input.read_bytes().decode('utf-8')
        stages = pdal.pipeline._parse_stages(j)
        p = pdal.Pipeline(stages)

        # strip off any writers we're making our own
        stages = []
        for stage in p.stages:
            if stage.type.split('.')[0] != 'writers':
                stages.append(stage)

        p = pdal.Pipeline(stages)
        return p




