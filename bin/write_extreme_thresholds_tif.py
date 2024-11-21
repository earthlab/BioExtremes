import os

from argparse import ArgumentParser
from era5.compute_thresholds import Drought, Wind

PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, 'data')


def drought_parser(subparser):
    drought = subparser.add_parser('drought', help='Compute drought thresholds')
    drought.add_argument('--gmw_dir', type=str, default=os.path.join(DATA_DIR, 'gmw_v3_2020'),
                         help='Path to GMW directory')
    drought.add_argument('--era5_dir', type=str, required=True, help='Path to ERA5 directory')
    drought.add_argument('--output_file', type=str, help='Output file path')
    drought.add_argument('--percentile', type=int, default=5, help='Percentile for drought computation')
    return drought


def wind_parser(subparser):
    wind = subparser.add_parser('wind', help='Compute wind thresholds')
    wind.add_argument('--gmw_dir', type=str, default=os.path.join(DATA_DIR, 'gmw_v3_2020'), help='Path to GMW directory')
    wind.add_argument('--era5_dir', type=str, required=True, help='Path to ERA5 directory')
    wind.add_argument('--output_file', type=str, required=True, help='Output file path')
    wind.add_argument('--threshold', type=float, default=33, help='Threshold for wind computation')
    return wind


if __name__ == '__main__':
    parser = ArgumentParser(description="Compute thresholds for extreme weather events")
    subparsers = parser.add_subparsers(dest='extreme_event', help='Choose an extreme event type')

    drought_parser(subparsers)
    wind_parser(subparsers)

    args = parser.parse_args()

    if args.extreme_event == 'drought':
        if args.output_file is None:
            args.output_file = os.path.join(DATA_DIR, 'drought_thresholds.tif')
        t = Drought(args.gmw_dir, percentile=args.percentile)
        t.write_threshold_file(args.era5_dir, args.output_file)
    elif args.extreme_event == 'wind':
        if args.output_file is None:
            args.output_file = os.path.join(DATA_DIR, 'extreme_wind_thresholds.tif')
        t = Wind(args.gmw_dir)
        print(args.threshold)
        t.write_threshold_file(args.era5_dir, args.output_file, args.threshold)
    else:
        parser.print_help()
