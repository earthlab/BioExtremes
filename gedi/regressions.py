import collections
import os
from typing import Tuple, List

import numpy as np
from collections import defaultdict

import pandas as pd
from osgeo import gdal
import geopandas as gpd
from shapely.geometry import Point
from tqdm import tqdm

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, 'data')


class Combine:
    def __init__(self, drought_extreme_events_tif_file_path: str, wind_extreme_events_tif_file_path: str,
                 gedi_csv_files: List[str], marine_eco_regions_file: str = os.path.join(DATA_DIR, 'MEOW', 'meow_ecos.shp'),
                 mangrove_species_richness_file: str = os.path.join(DATA_DIR, 'Richness_CRENVU_2018',
                                                                    'Richness_crenvu.tif'),
                 gedi_columns: List[str] = ('rh98', 'pai', 'fhd')):
        self._gedi_csv_files = gedi_csv_files

        self._rain_extreme_events = gdal.Open(drought_extreme_events_tif_file_path)
        self._rain_extreme_events_array = self._rain_extreme_events.ReadAsArray()
        self._rain_extreme_events_geo_transform = self._rain_extreme_events.GetGeoTransform()

        self._wind_extreme_events = gdal.Open(wind_extreme_events_tif_file_path)
        self._wind_extreme_events_array = self._wind_extreme_events.ReadAsArray()
        self._wind_extreme_events_geo_transform = self._wind_extreme_events.GetGeoTransform()

        self._marine_eco_regions_gdf = gpd.read_file(marine_eco_regions_file) if marine_eco_regions_file is not None \
            else None
        self._mangrove_species_richness_raster = gdal.Open(mangrove_species_richness_file) if \
            mangrove_species_richness_file is not None else None

        self._gedi_regex = r"GEDI02_._(\d{4})\d{9}_O\d{5}_\d{2}_T\d{5}_\d{2}_\d{3}_\d{2}_V\d{3}\.h5"

        print('Creating correlations DataFrame')
        self.df = self._combine(gedi_columns)

    def _era5_index_to_traditional_deg(self, lat_idx, lon_idx):
        lat, lon = ((self._wind_extreme_events_geo_transform[5] * lat_idx) + self._wind_extreme_events_geo_transform[3],
                    (self._wind_extreme_events_geo_transform[1] * lon_idx) + self._wind_extreme_events_geo_transform[0])
        lon -= 180
        return lat, lon

    def _traditional_deg_to_era5_index(self, gedi_lat, gedi_lon):
        """
        GEDI longitudes are in [-180, 180] while era5 rasters are in [0, 360]
        """
        lon_idx = int(
            (gedi_lon + 180) / self._wind_extreme_events_geo_transform[1])
        lat_idx = int(
            (gedi_lat - self._wind_extreme_events_geo_transform[3]) /
            self._wind_extreme_events_geo_transform[5])
        return lat_idx, lon_idx

    def _era5_index_to_crenvu_index(self, era5_lat_idx, era5_lon_idx):
        lat, lon = self._era5_index_to_traditional_deg(era5_lat_idx, era5_lon_idx)
        species_gt = self._mangrove_species_richness_raster.GetGeoTransform()
        species_lat_idx = int((lat - species_gt[3]) / species_gt[5])
        species_lon_idx = int((lon - species_gt[0]) / species_gt[1])
        return species_lat_idx, species_lon_idx

    def _get_marine_eco_region(self, era5_lat_idx, era5_lon_idx):
        lat, lon = self._era5_index_to_traditional_deg(era5_lat_idx, era5_lon_idx)
        point = Point(lon, lat)

        # Find the row whose geometry contains the point
        containing_rows = self._marine_eco_regions_gdf[self._marine_eco_regions_gdf.contains(point)]

        # Check if any rows were found
        return 'NULL' if containing_rows.empty else containing_rows.iloc[0]['REALM']

    def _get_mangrove_species_count(self, era5_lat_idx, era5_lon_idx):
        species_lat_idx, species_lon_idx = self._era5_index_to_crenvu_index(era5_lat_idx, era5_lon_idx)
        return self._mangrove_species_richness_raster.ReadAsArray()[species_lat_idx][species_lon_idx]

    def _extract_from_files(self, gedi_columns):
        values = defaultdict(dict)
        for gedi_csv in self._gedi_csv_files:
            gedi_data = pd.read_csv(gedi_csv)
            for index, row in tqdm(gedi_data.iterrows(), total=len(gedi_data)):
                lat_idx, lon_idx = self._traditional_deg_to_era5_index(row['latitude'], row['longitude'])
                if (lat_idx, lon_idx) not in values:
                    values[(lat_idx, lon_idx)] = collections.defaultdict(list)
                for gedi_column in gedi_columns:
                    if gedi_column in gedi_data:
                        values[(lat_idx, lon_idx)][gedi_column].append(row[gedi_column])

        return {k: {k1: np.median(v1) for k1, v1 in values[k].items()} for k, v in values.items()}

    def _combine(self, gedi_columns, add_marine_eco_region_column: bool = True,
                 add_species_richness_column: bool = True):
        vals = self._extract_from_files(gedi_columns)

        df_copy = pd.DataFrame()
        df_copy['drought_intensity'] = pd.Series(dtype=float)
        df_copy['drought_duration'] = pd.Series(dtype=float)
        df_copy['drought_frequency'] = pd.Series(dtype=float)
        df_copy['drought_time_since_last_event'] = pd.Series(dtype=float)

        df_copy['wind_intensity'] = pd.Series(dtype=float)
        df_copy['wind_duration'] = pd.Series(dtype=float)
        df_copy['wind_frequency'] = pd.Series(dtype=float)
        df_copy['wind_time_since_last_event'] = pd.Series(dtype=float)
        df_copy['lat_idx'] = pd.Series(dtype=int)
        df_copy['lon_idx'] = pd.Series(dtype=int)

        if add_marine_eco_region_column is not None:
            df_copy['marine_eco_region'] = pd.Series(dtype=str)
        if add_species_richness_column is not None:
            df_copy['mangrove_species_count'] = pd.Series(dtype=int)

        for index, (k, v) in enumerate(vals.items()):
            lat_idx = k[0]
            lon_idx = k[1]
            for gedi_column in gedi_columns:
                df_copy.at[index, gedi_column] = v[gedi_column] if gedi_column in v else None

            df_copy.at[index, 'wind_intensity'] = self._wind_extreme_events_array[0, lat_idx, lon_idx]
            df_copy.at[index, 'wind_duration'] = self._wind_extreme_events_array[1, lat_idx, lon_idx]
            df_copy.at[index, 'wind_frequency'] = self._wind_extreme_events_array[2, lat_idx, lon_idx]
            df_copy.at[index, 'wind_time_since_last_event'] = self._wind_extreme_events_array[3, lat_idx, lon_idx]

            df_copy.at[index, 'drought_intensity'] = self._rain_extreme_events_array[0, lat_idx, lon_idx]
            df_copy.at[index, 'drought_duration'] = self._rain_extreme_events_array[1, lat_idx, lon_idx]
            df_copy.at[index, 'drought_frequency'] = self._rain_extreme_events_array[2, lat_idx, lon_idx]
            df_copy.at[index, 'drought_time_since_last_event'] = self._rain_extreme_events_array[3, lat_idx, lon_idx]

            df_copy.at[index, 'lat_idx'] = lat_idx
            df_copy.at[index, 'lon_idx'] = lon_idx

            if add_marine_eco_region_column:
                df_copy.at[index, 'marine_eco_region'] = self._get_marine_eco_region(lat_idx, lon_idx)
            if add_species_richness_column:
                df_copy.at[index, 'mangrove_species_count'] = self._get_mangrove_species_count(lat_idx, lon_idx)

        return df_copy

    def split_by_eco_region(self, out_dir: str):
        os.makedirs(out_dir, exist_ok=True)
        unique_eco_regions = set(self.df['marine_eco_region'])
        for eco_region in unique_eco_regions:
            eco_region_df = self.df[self.df['marine_eco_region'] == eco_region]
            eco_region_df.to_csv(os.path.join(out_dir, eco_region.lower().replace(' ', '_') + '.csv'))

    def split_by_species_richness(self, out_dir: str,
                                  ranges: Tuple[Tuple[int, int]] = ((1, 3), (4, 13), (14, 25), (26, 35), (36, 46))):
        os.makedirs(out_dir, exist_ok=True)
        for species_range in ranges:
            species_richness_df = self.df[np.logical_and(species_range[0] <= self.df['mangrove_species_count'],
                                                         self.df['mangrove_species_count'] <= species_range[1])]
            species_richness_df.to_csv(
                os.path.join(out_dir, f'species_richness_{species_range[0]}_{species_range[1]}.csv'))


def combine_csv_files(year_dirs, combined_dir):
    # Create output directories if they don't exist
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


def combine_all_years():
    # for year in ['2019', '2020', '2021', '2022']:
    #     c = Combine(os.path.join('data', f'extreme_drought_{year}.tif'),
    #                 os.path.join('data', 'extreme_wind_{year}.tif'),
    #                 [os.path.join('data', f'l2a_{year}.csv'),
    #                  os.path.join('data', f'l2b_{year}.csv')])
    #
    #     c.split_by_eco_region(os.path.join('data', 'gedi_era5_combined', year))
    #     c.split_by_species_richness(os.path.join('data', 'gedi_era5_combined', year))

    # Example usage
    year_dirs = ['data/gedi_era5_combined/2019', 'data/gedi_era5_combined/2020',
                 'data/gedi_era5_combined/2021', 'data/gedi_era5_combined/2022']
    combined_dir = 'data/gedi_era5_combined/combined'

    combine_csv_files(year_dirs, combined_dir)
