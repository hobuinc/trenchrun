from . import logs

import json
import tempfile
import subprocess
import shlex
import pathlib

import pdal


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

class Data(object):
    def __init__(self, args):

        self.args = args

        if '.json' in self.args.input.suffixes:
            self.inputType = 'pipeline'
        else:
            self.inputType = 'readable'

        self.args.intensityPath = pathlib.Path(tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name)
        self.args.dsmPath = pathlib.Path(tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name)
        self.args.aoPath = pathlib.Path(tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name)
        self.checkValidData()

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


    def readFile(self):
        reader = pdal.Reader(str(self.args.input))
        pipeline = reader.pipeline()
        return pipeline

    def __del__(self):
        self.args.intensityPath.unlink()
        self.args.dsmPath.unlink()
        self.args.aoPath.unlink()

    def checkValidData(self):

        if self.inputType == 'pipeline':
            reader = self.readPipeline()
        else:
            reader = self.readFile()

        qi = reader.quickinfo
        for key in qi:
            dimensions = [i.strip() for i in qi[key]['dimensions'].split(',')]
            if 'Intensity' not in dimensions:
                raise RuntimeError("Intensity information not available, this tool cannot run")

    def getReader(self):
        reader = None
        if self.args.reader_args:
            with open(self.args.reader_args,'r') as f:
                j = json.loads(f.read())
            reader = pdal.Reader(filename=str(self.args.input), *j)
        else:
            reader = pdal.Reader(filename=str(self.args.input))
        return reader

    def getWriters(self):
        intensity = pdal.Writer.gdal(
            filename=str(self.args.intensityPath),
            data_type='uint16_t',
            dimension='Intensity',
            output_type = 'idw',
            resolution=self.args.resolution,
        )
        dsm = pdal.Writer.gdal(
            filename=str(self.args.dsmPath),
            data_type='float',
            dimension='Z',
            output_type = 'idw',
            resolution=self.args.resolution,
        )
        return intensity | dsm

    def getPipeline(self):
        if self.inputType == 'pipeline':
            reader = self.readPipeline()
        else:
            reader = self.readFile()

        writers = self.getWriters()
        stage = reader | writers

        return stage


    def execute(self):
        pipeline = self.getPipeline()
        count = 0
        if pipeline.streamable:
            count = pipeline.execute_streaming(chunk_size=self.args.chunk_size)
        else:
            count = pipeline.execute()
        logs.logger.info(f'Wrote intensity and dsm for {count} points')

    def getImageCenter(self):
        # Run our pipeline

        command = f'gdalinfo -json {self.args.dsmPath}'
        response = run(command)
        j = json.loads(response)
        corner = j['wgs84Extent']['coordinates'][0][0]
        logs.logger.info(f'Fetched image center {corner}')
        return corner
    def ambient_occlusion(self):
        lng, lat = self.getImageCenter()

        command = f"""whitebox_tools -r=TimeInDaylight  \
        -i {self.args.dsmPath} -o {self.args.aoPath}  --az_fraction=15.0 \
        --max_dist=100.0 --lat={lat:.5f} --long={lng:.5f} """
        logs.logger.info(f"Processing ambient occlusion '{command}'")
        response = run(command)
        logs.logger.info(f"Processed ambient occlusion ")


