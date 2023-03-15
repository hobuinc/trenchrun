
from . import logs 
from . import do
from . import argparser
import sys


def main():
    args = argparser.get_parser(sys.argv[1:])
    if args.debug:
        logs.logger.setLevel(logs.logging.DEBUG)
        logs.handler.setLevel(logs.logging.DEBUG)

    do.doIt(args)


if __name__ == "__main__":
    sys.exit(main())


