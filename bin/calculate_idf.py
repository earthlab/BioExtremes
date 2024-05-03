from argparse import ArgumentParser

from era5.extreme_events import Precipitation
from datetime import datetime

if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('--thresh')
    args.add_argument('--in_dir')
    args.add_argument('--out_file')

    args = args.parse_args()

    p = Precipitation(args.thresh)
    p.create_idf_tif(args.in_dir, datetime(1979, 1, 1), datetime(2018, 12, 31),
                     month_window=1, outfile=args.out_file)
