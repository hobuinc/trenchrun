from . import data
from . import blend
from .logs import logger


def doIt(args):
    logger.info(f"opening {args.input} for processing")
    reader = data.Reader(args)

    intensity = data.Intensity(reader)
    dsm = data.DSM(reader)

    dsm.process()
    intensity.process()

    daylight = data.Daylight(dsm)
    daylight.process()

    b = blend.Blend(intensity, dsm, daylight)
    b.write(args)