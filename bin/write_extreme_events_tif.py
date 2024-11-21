import sys
import os
from argparse import ArgumentParser

from era5.extreme_events import Drought, Wind
from datetime import datetime


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('--type', type=str, choices=['drought', 'wind'], required=True,
                      help='Type of weather to calculate extreme events for. Can be either wind or drought')
    args.add_argument('--threshold_tif', type=str, help='Path to the tif file of threshold values',
                      required=True)
    args.add_argument('--era5_dir', type=str, required=True,
                      help='Path to directory containing era5 tif files of weather values')
    args.add_argument('--output_file', type=str, help='Path to save output tif file to')
    args.add_argument('--end_year', type=int, required=True,
                      help='The cutoff year for which era5 files will be used to search for extreme events.')
    args.add_argument('--window', type=int, required=True,
                      help='The minimum consecutive time steps weather must be above / below threshold to be '\
                           ' considered extreme. Wind resolution is 6 hours and precipitation is 1 month')

    args = args.parse_args()

    if args.type == 'wind':
        if args.output_file is None:
            args.output_file = os.path.join(DATA_DIR, f'extreme_wind_{args.end_year + 1}.tif')
        e = Wind(args.threshold_tif)
    elif args.type == 'drought':
        if args.output_file is None:
            args.output_file = os.path.join(DATA_DIR, f'drought_{args.end_year + 1}.tif')
        e = Drought(args.threshold_tif)
    else:
        sys.exit(2)

    e.create_idf_tif(args.era5_dir, datetime(1979, 1, 1), datetime(args.end_year, 12, 31),
                     window=args.window, outfile=args.output_file)
