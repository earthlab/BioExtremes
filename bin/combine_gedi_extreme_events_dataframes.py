import os
import argparse
import pandas as pd


def combine_csv_files(year_dirs, combined_dir):
    # Create output directories if they don't exist
    os.makedirs(combined_dir, exist_ok=True)
    file_dict = {}
    # Iterate over each year directory
    for year_dir in year_dirs:
        if os.path.exists(year_dir):
            # List all CSV files in the current subdirectory
            for file in os.listdir(year_dir):
                if file.endswith('.csv'):
                    if file not in file_dict:
                        file_dict[file] = []
                    # Append the current file path to the dictionary
                    file_dict[file].append(os.path.join(year_dir, file))

    # Combine and save files with the same name
    for file in file_dict:
        paths = file_dict[file]
        combined_df = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
        combined_df.to_csv(os.path.join(combined_dir, file), index=False)
    print(f"Combined files saved to: {combined_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Combine CSV files from multiple year directories into a single directory."
    )
    parser.add_argument(
        "-y", "--year_dirs",
        nargs="+",
        required=True,
        help="List of directories containing yearly CSV files."
    )
    parser.add_argument(
        "-o", "--output_dir",
        required=True,
        help="Directory to save the combined CSV files."
    )

    args = parser.parse_args()
    year_dirs = args.year_dirs
    output_dir = args.output_dir

    combine_csv_files(year_dirs, output_dir)


if __name__ == "__main__":
    main()
