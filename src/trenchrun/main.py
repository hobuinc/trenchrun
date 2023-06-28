
from . import logs 
from . import do
from . import argparser
from . import rls
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


if __name__ == "__main__":
    sys.exit(trenchrun_main())


