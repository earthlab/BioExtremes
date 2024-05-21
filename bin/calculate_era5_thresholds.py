from argparse import ArgumentParser
from era5.compute_thresholds import ComputeThresholds


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--gmw_dir', type=str)
    parser.add_argument('--era5_dir', type=str)
    parser.add_argument('--out_file', type=str)
    parser.add_argument('--extreme_event', type=str)
    parser.add_argument('--percentile', type=int)

    args = parser.parse_args()

    c = ComputeThresholds(args.gmw_dir, percentile=args.percentile)

    if args.extreme_event == 'precipitation':
        c.compute_era5_total_precipitation_threshold(args.era5_dir, args.out_file)
    elif args.extreme_event == 'wind':
        c.compute_era5_wind_speed_threshold(args.era5_dir, args.out_file)
    else:
        raise ValueError('extreme_event arg must be precipitation or wind')
