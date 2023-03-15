from . import data
from . import blend
from .logs import logger 


def doIt(args):
    logger.info(f"opening {args.input} for processing")
    d = data.Data(args)
    d.execute()
    d.ambient_occlusion()

    b = blend.Blend(d)
    b.do()