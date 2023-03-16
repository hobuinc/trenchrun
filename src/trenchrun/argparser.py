import pathlib


def get_parser(args):

    import argparse

    parser = argparse.ArgumentParser(description='Compute the Ambient Absorption imagery product for lidar')
    parser.add_argument('input',
                        help='PDAL-readable lidar content', type=pathlib.Path)
    parser.add_argument('--output',
                        help='Output filename', type=str, default='exposure')
    parser.add_argument('--filters',
                        help='Filter stages', type =str, default=None)
    parser.add_argument('--reader_args',
                        help='PDAL Reader args as JSON object', type =str, default=None)
    parser.add_argument('--resolution',
                        help='Raster output resolution', type =float, default=1.0)
    parser.add_argument('--alpha',
                        help='Amount of alpha for blend', type =float, default=0.85)
    parser.add_argument('--chunk_size',
                        help='PDAL streaming chunk size', type =int, default=int(1e6))
    parser.add_argument('--blue',
                        help='Use blue shade intensity', default=True)
    parser.add_argument('--full-output',
                        help='Output all intermediate output', default=True)
    parser.add_argument('--debug',
                        action='store_true',
                        help='print debug messages to stderr')


    args = parser.parse_args(args)
    return args
