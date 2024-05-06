import sys
from argparse import ArgumentParser

from era5.extreme_events import Precipitation, Wind
from datetime import datetime

if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('--thresh')
    args.add_argument('--in_dir')
    args.add_argument('--out_file')
    args.add_argument('--type')
    args.add_argument('--end_year', type=int)

    args = args.parse_args()

    if args.type == 'wind':
        e = Wind(args.thresh)
    elif args.type == 'rain':
        e = Precipitation(args.thresh)
    else:
        sys.exit(2)

    e.create_idft_tif(args.in_dir, datetime(1979, 1, 1), datetime(args.end_year, 12, 31),
                      window=1, outfile=args.out_file)
