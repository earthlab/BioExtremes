import argparse
import os
from gedi.regressions import Combine


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process GEDI data by eco region and species richness.")
    parser.add_argument("--drought_path", required=True, help="Path to drought extreme events TIFF file.")
    parser.add_argument("--wind_path", required=True, help="Path to wind extreme events TIFF file.")
    parser.add_argument("--gedi_csvs", nargs='+', required=True, help="Path to the GEDI CSV files.")
    parser.add_argument("--marine_eco_regions", default=os.path.join(DATA_DIR, 'MEOW', 'meow_ecos.shp'),
                        help="Path to the marine eco regions shapefile.")
    parser.add_argument("--species_richness",
                        default=os.path.join(DATA_DIR, 'Richness_CRENVU_2018', 'Richness_crenvu.tif'),
                        help="Path to the species richness TIFF file.")
    parser.add_argument("--output_dir", required=True, help="Directory to save the output files.")
    parser.add_argument("--richness-ranges", nargs="+", type=int, default=[1, 3, 4, 13, 14, 25, 26, 35, 36, 46],
                        help="Ranges for species richness split, e.g., 1 3 4 13 14 25.")

    args = parser.parse_args()

    processor = Combine(args.drought_path, args.wind_path, args.gedi_csvs, args.marine_eco_regions,
                        args.species_richness)

    # Handle splitting
    processor.split_by_eco_region(args.output_dir)
    ranges = list(zip(args.richness_ranges[::2], args.richness_ranges[1::2]))
    processor.split_by_species_richness(args.output_dir, ranges)

    print(f"Processing complete. Output saved to {args.output_dir}")
