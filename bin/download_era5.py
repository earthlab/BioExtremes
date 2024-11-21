import argparse
import os
from datetime import datetime
from typing import List
from era5.api import MonthlySingleLevelInstantaneous, HourlySingleLevelInstantaneous


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def validate_date(date_str: str) -> str:
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD.")


def parse_hour_filter(hours_str: str) -> List[int]:
    try:
        hours = [int(hour) for hour in hours_str.split(',')]
        if any(hour < 0 or hour > 23 for hour in hours):
            raise ValueError
        return hours
    except ValueError:
        raise argparse.ArgumentTypeError("Hour filter must be a comma-separated list of integers between 0 and 23.")


def main():
    parser = argparse.ArgumentParser(description="Download climate data files from the specified dataset.")

    # Dataset type selection
    parser.add_argument(
        "--dataset",
        choices=["monthly", "hourly"],
        required=True,
        help="Choose the dataset type: 'monthly' or 'hourly'."
    )

    # Date range
    parser.add_argument(
        "--start_date",
        type=validate_date,
        required=True,
        help="Start date in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--end_date",
        type=validate_date,
        required=True,
        help="End date in YYYY-MM-DD format."
    )

    # Output directory
    parser.add_argument(
        "--output_dir",
        type=str,
        help="Directory to save downloaded files."
    )

    # Optional hour filter for hourly dataset
    parser.add_argument(
        "--hour_filter",
        type=parse_hour_filter,
        required=False,
        help="Comma-separated list of hours (0-23) to filter for hourly data (e.g., '0,6,12,18')."
    )

    args = parser.parse_args()

    if args.output_dir is None:
        args.output_dir = os.path.join(DATA_DIR, 'era5', 'tp' if args.dataset == 'monthly' else 'i10fg')

    # Ensure the output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize the appropriate API class and start the download process
    if args.dataset == "monthly":
        downloader = MonthlySingleLevelInstantaneous()
        downloader.download(
            start_date=args.start_date,
            end_date=args.end_date,
            out_dir=args.output_dir,
            var='tp'
        )
    elif args.dataset == "hourly":
        downloader = HourlySingleLevelInstantaneous()
        downloader.download(
            start_date=args.start_date,
            end_date=args.end_date,
            out_dir=args.output_dir,
            var='i10fg',
            hour_filter=args.hour_filter
        )


if __name__ == "__main__":
    main()
