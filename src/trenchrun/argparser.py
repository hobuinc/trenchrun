import pathlib


def get_trenchrun_parser(args):

    import argparse

    parser = argparse.ArgumentParser(description='Compute the Ambient Absorption imagery product for lidar')
    parser.add_argument('input',
                        help='PDAL-readable lidar content as a file or a pipeline', type=pathlib.Path)
    parser.add_argument('--output',
                        help='Output filename', type=str, default='exposure')
    parser.add_argument('--output-path',
                        help='Path to write output data', type=pathlib.Path, default=pathlib.Path.cwd())
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

def get_rls_parser(args):

    import argparse

    parser = argparse.ArgumentParser(description='Compute a line of sight mask along a route for a digital surface model and a line ')
    parser.add_argument('input',
                        help='GDAL-readable DSM content', type=pathlib.Path)
    parser.add_argument('line',
                        help='Linestring to use for RLS', type=str)
    parser.add_argument('--line_srs',
                        help='SRS of Linestring (assumed EPSG:4326 if not specified)', type=str)
    parser.add_argument('--output',
                        help='Output mask filename', type=str, default='rls-mask')
    parser.add_argument('--output-path',
                        help='Path to write output data', type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument('--height',
                        help='Target height to compute viewshed', type=float, default=2.0)
    parser.add_argument('--density',
                        help='Step density along the line to compute viewsheds', type=float, default=10.0)
    parser.add_argument('--range',
                        help='Range to compute maximum visibility (500m)', type=int, default=int(500))
    parser.add_argument('--debug',
                        action='store_true',
                        help='print debug messages to stderr')


    args = parser.parse_args(args)
    return args

def get_builder_parser(args):

    import argparse

    parser = argparse.ArgumentParser(description='Build a PDAL pipeline for a given EPT and GeoJSON geometry that is suitable for Trenchrun')
    parser.add_argument('ept',
                        help='EPT to use for fetching content', type=str)
    parser.add_argument('geojson',
                        help='GeoJSON geometry describing footprint', type=pathlib.Path)
    parser.add_argument('--output',
                        help='Output filename', type=pathlib.Path, default='output-pipeline.json')
    parser.add_argument('--buffer',
                        help='Buffer the geometry', type=float, default=float('nan') )
    parser.add_argument('--debug',
                        action='store_true',
                        help='print debug messages to stderr')


    args = parser.parse_args(args)
    return args