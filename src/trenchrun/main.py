
from . import logs
from . import do
from . import argparser
from . import rls
from . import builder
import sys

def rls_main():
    args = argparser.get_rls_parser(sys.argv[1:])
    if args.debug:
        logs.logger.setLevel(logs.logging.DEBUG)
        logs.handler.setLevel(logs.logging.DEBUG)

    rls.do(args)

def trenchrun_main():
    args = argparser.get_trenchrun_parser(sys.argv[1:])
    if args.debug:
        logs.logger.setLevel(logs.logging.DEBUG)
        logs.handler.setLevel(logs.logging.DEBUG)

    do.doIt(args)

def pipeline_builder_main():
    args = argparser.get_builder_parser(sys.argv[1:])
    if args.debug:
        logs.logger.setLevel(logs.logging.DEBUG)
        logs.handler.setLevel(logs.logging.DEBUG)

    builder.do(args)


if __name__ == "__main__":
    sys.exit(trenchrun_main())


