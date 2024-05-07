import re
import os

import pandas as pd
from osgeo import gdal


class Base:
    def __init__(self, rain_extreme_events_tif_file_path: str, wind_extreme_events_tif_file_path: str,
                 gedi_l2a_in_dir: str, gedi_l2b_in_dir: str):
        self._gedi_l2a_in_dir = gedi_l2a_in_dir
        self._gedi_l2b_in_dir = gedi_l2b_in_dir

        self._rain_extreme_events = gdal.Open(rain_extreme_events_tif_file_path)
        self._rain_extreme_events_array = self._rain_extreme_events.ReadAsArray()
        self._rain_extreme_events_geotransform = self._rain_extreme_events.GetGeoTransform()

        self._wind_extreme_events = gdal.Open(wind_extreme_events_tif_file_path)
        self._wind_extreme_events_array = self._wind_extreme_events.ReadAsArray()
        self._wind_extreme_events_geotransform = self._wind_extreme_events.GetGeoTransform()

        self._gedi_regex = r"GEDI02_._(\d{4})\d{9}_O\d{5}_\d{2}_T\d{5}_\d{2}_\d{3}_\d{2}_V\d{3}\.h5"

    def _combine(self, in_dir, year):
        combined_csvs = []
        for gedi_csv in os.listdir(in_dir):
            match = re.match(self._gedi_regex, gedi_csv)
            if not match:
                continue

            file_year = int(match.group(1))
            if file_year != year:
                continue

            gedi_data = pd.read_csv(os.path.join(in_dir, gedi_csv))

            df_copy = gedi_data.copy()

            # Add eight new columns to the copied DataFrame with initial values as NaN
            df_copy['rain_intensity'] = pd.Series(dtype=float)
            df_copy['rain_duration'] = pd.Series(dtype=float)
            df_copy['rain_frequency'] = pd.Series(dtype=float)
            df_copy['rain_time_since_last_event'] = pd.Series(dtype=float)

            df_copy['wind_intensity'] = pd.Series(dtype=float)
            df_copy['wind_duration'] = pd.Series(dtype=float)
            df_copy['wind_frequency'] = pd.Series(dtype=float)
            df_copy['wind_time_since_last_event'] = pd.Series(dtype=float)

            for index, row in df_copy.iterrows():
                wind_lon_idx = int(
                    (row['longitude'] - self._wind_extreme_events_geotransform[0]) /
                    self._wind_extreme_events_geotransform[1])
                wind_lat_idx = int(
                    (row['latitude'] - self._wind_extreme_events_geotransform[3]) /
                    self._wind_extreme_events_geotransform[5])

                rain_lon_idx = int(
                    (row['longitude'] - self._rain_extreme_events_geotransform[0]) /
                    self._rain_extreme_events_geotransform[1])
                rain_lat_idx = int(
                    (row['latitude'] - self._rain_extreme_events_geotransform[3]) /
                    self._rain_extreme_events_geotransform[5])

                df_copy.at[index, 'wind_intensity'] = self._wind_extreme_events_array[0, wind_lat_idx, wind_lon_idx]
                df_copy.at[index, 'wind_duration'] = self._wind_extreme_events_array[1, wind_lat_idx, wind_lon_idx]
                df_copy.at[index, 'wind_frequency'] = self._wind_extreme_events_array[2, wind_lat_idx, wind_lon_idx]
                df_copy.at[index, 'wind_time_since_last_event'] = self._wind_extreme_events_array[3, wind_lat_idx,
                wind_lon_idx]

                df_copy.at[index, 'rain_intensity'] = self._rain_extreme_events_array[0, rain_lat_idx, rain_lon_idx]
                df_copy.at[index, 'rain_duration'] = self._rain_extreme_events_array[1, rain_lat_idx, rain_lon_idx]
                df_copy.at[index, 'rain_frequency'] = self._rain_extreme_events_array[2, rain_lat_idx, rain_lon_idx]
                df_copy.at[index, 'rain_time_since_last_event'] = self._rain_extreme_events_array[3, rain_lat_idx,
                rain_lon_idx]

            combined_csvs.append(df_copy)
        combined_csvs = pd.concat(combined_csvs)
        combined_csvs.reset_index(inplace=True)

        return combined_csvs

    def combine_extreme_events_and_gedi(self, out_file: str, year: int):
        l2a_csv, l2b_csv = self._combine(self._gedi_l2a_in_dir, year), self._combine(self._gedi_l2b_in_dir, year)
        l2a_csv.to_csv('l2a_2019.csv')
        l2b_csv.to_csv('l2b_2019.csv')
        # print(len(l2a_csv), len(l2b_csv))
        # merged_df = pd.merge(l2a_csv, l2b_csv, on=['latitude', 'longitude'], how='inner')
        # merged_df.reset_index(inplace=True)
        # merged_df.to_csv(out_file)
