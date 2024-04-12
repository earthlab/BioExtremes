from argparse import ArgumentParser
from era5.compute_thresholds import ComputeThresholds


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--gmw_dir', type=str)
    parser.add_argument('--era5_dir', type=str)
    parser.add_argument('--out_file', type=str)
    args = parser.parse_args()

    c = ComputeThresholds(args.gmw_dir)

    c.compute_era5_wind_speed_threshold(args.era5_dir, args.out_file)
