import re
import os
import numpy as np
from collections import defaultdict

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

    def _combine_l2a(self, in_dir, year):
        vals = defaultdict(list)
        for gedi_csv in os.listdir(in_dir):
            match = re.match(self._gedi_regex, gedi_csv)
            if not match:
                continue

            file_year = int(match.group(1))
            if file_year != year:
                continue

            gedi_data = pd.read_csv(os.path.join(in_dir, gedi_csv))

            df_copy = gedi_data.copy()

            for index, row in df_copy.iterrows():
                lon_idx = int(
                    (row['longitude'] - self._wind_extreme_events_geotransform[0]) /
                    self._wind_extreme_events_geotransform[1])
                lat_idx = int(
                    (row['latitude'] - self._wind_extreme_events_geotransform[3]) /
                    self._wind_extreme_events_geotransform[5])

                vals[(lat_idx, lon_idx)].append(row['rh98'])

        df_copy = pd.DataFrame()
        df_copy['rain_intensity'] = pd.Series(dtype=float)
        df_copy['rain_duration'] = pd.Series(dtype=float)
        df_copy['rain_frequency'] = pd.Series(dtype=float)
        df_copy['rain_time_since_last_event'] = pd.Series(dtype=float)

        df_copy['wind_intensity'] = pd.Series(dtype=float)
        df_copy['wind_duration'] = pd.Series(dtype=float)
        df_copy['wind_frequency'] = pd.Series(dtype=float)
        df_copy['wind_time_since_last_event'] = pd.Series(dtype=float)
        df_copy['wind_s'] = pd.Series(dtype=float)
        df_copy['wind_intensity_time'] = pd.Series(dtype=float)
        df_copy['wind_duration_time'] = pd.Series(dtype=float)
        df_copy['wind_s_time'] = pd.Series(dtype=float)

        for index, (k, v) in enumerate(vals.items()):
            df_copy.at[index, 'rh_98'] = np.median(v)
            lat_idx = k[0]
            lon_idx = k[1]

            df_copy.at[index, 'wind_intensity'] = self._wind_extreme_events_array[0, lat_idx, lon_idx]
            df_copy.at[index, 'wind_duration'] = self._wind_extreme_events_array[1, lat_idx, lon_idx]
            df_copy.at[index, 'wind_frequency'] = self._wind_extreme_events_array[2, lat_idx, lon_idx]
            df_copy.at[index, 'wind_time_since_last_event'] = self._wind_extreme_events_array[3, lat_idx, lon_idx]
            df_copy.at[index, 'wind_s'] = self._wind_extreme_events_array[4, lat_idx, lon_idx]
            df_copy.at[index, 'wind_intensity_time'] = self._wind_extreme_events_array[
                5, lat_idx, lon_idx]
            df_copy.at[index, 'wind_duration_time'] = self._wind_extreme_events_array[6, lat_idx, lon_idx]
            df_copy.at[index, 'wind_s_time'] = self._wind_extreme_events_array[7, lat_idx, lon_idx]

            df_copy.at[index, 'rain_intensity'] = self._rain_extreme_events_array[0, lat_idx, lon_idx]
            df_copy.at[index, 'rain_duration'] = self._rain_extreme_events_array[1, lat_idx, lon_idx]
            df_copy.at[index, 'rain_frequency'] = self._rain_extreme_events_array[2, lat_idx, lon_idx]
            df_copy.at[index, 'rain_time_since_last_event'] = self._rain_extreme_events_array[3, lat_idx, lon_idx]

        return df_copy

    def _combine_l2b(self, in_dir, year):
        fhd_vals = defaultdict(list)
        pai_vals = defaultdict(list)
        for gedi_csv in os.listdir(in_dir):
            match = re.match(self._gedi_regex, gedi_csv)
            if not match:
                continue

            file_year = int(match.group(1))
            if file_year != year:
                continue

            gedi_data = pd.read_csv(os.path.join(in_dir, gedi_csv))
            df_copy = gedi_data.copy()

            for index, row in df_copy.iterrows():
                lon_idx = int(
                    (row['longitude'] - self._wind_extreme_events_geotransform[0]) /
                    self._wind_extreme_events_geotransform[1])
                lat_idx = int(
                    (row['latitude'] - self._wind_extreme_events_geotransform[3]) /
                    self._wind_extreme_events_geotransform[5])

                fhd_vals[(lat_idx, lon_idx)].append(row['fhd'])
                pai_vals[(lat_idx, lon_idx)].append(row['pai'])

        df_copy = pd.DataFrame()
        df_copy['rain_intensity'] = pd.Series(dtype=float)
        df_copy['rain_duration'] = pd.Series(dtype=float)
        df_copy['rain_frequency'] = pd.Series(dtype=float)
        df_copy['rain_time_since_last_event'] = pd.Series(dtype=float)

        df_copy['wind_intensity'] = pd.Series(dtype=float)
        df_copy['wind_duration'] = pd.Series(dtype=float)
        df_copy['wind_frequency'] = pd.Series(dtype=float)
        df_copy['wind_time_since_last_event'] = pd.Series(dtype=float)
        df_copy['wind_s'] = pd.Series(dtype=float)
        df_copy['wind_intensity_time'] = pd.Series(dtype=float)
        df_copy['wind_duration_time'] = pd.Series(dtype=float)
        df_copy['wind_s_time'] = pd.Series(dtype=float)

        for index, (k, v) in enumerate(fhd_vals.items()):
            df_copy.at[index, 'fhd'] = np.median(v)
            df_copy.at[index, 'pai'] = np.median(pai_vals[k])
            lat_idx = k[0]
            lon_idx = k[1]

            df_copy.at[index, 'wind_intensity'] = self._wind_extreme_events_array[0, lat_idx, lon_idx]
            df_copy.at[index, 'wind_duration'] = self._wind_extreme_events_array[1, lat_idx, lon_idx]
            df_copy.at[index, 'wind_frequency'] = self._wind_extreme_events_array[2, lat_idx, lon_idx]
            df_copy.at[index, 'wind_time_since_last_event'] = self._wind_extreme_events_array[3, lat_idx,
            lon_idx]
            df_copy.at[index, 'wind_s'] = self._wind_extreme_events_array[4, lat_idx, lon_idx]
            df_copy.at[index, 'wind_intensity_time'] = self._wind_extreme_events_array[5, lat_idx, lon_idx]
            df_copy.at[index, 'wind_duration_time'] = self._wind_extreme_events_array[6, lat_idx, lon_idx]
            df_copy.at[index, 'wind_s_time'] = self._wind_extreme_events_array[7, lat_idx, lon_idx]

            df_copy.at[index, 'rain_intensity'] = self._rain_extreme_events_array[0, lat_idx, lon_idx]
            df_copy.at[index, 'rain_duration'] = self._rain_extreme_events_array[1, lat_idx, lon_idx]
            df_copy.at[index, 'rain_frequency'] = self._rain_extreme_events_array[2, lat_idx, lon_idx]
            df_copy.at[index, 'rain_time_since_last_event'] = self._rain_extreme_events_array[3, lat_idx, lon_idx]

        return df_copy

    def combine_extreme_events_and_gedi(self, out_file: str, year: int):
        l2a_csv = self._combine_l2a(self._gedi_l2a_in_dir, year)
        l2a_csv.to_csv('l2a_2019.csv')
        l2b_csv = self._combine_l2b(self._gedi_l2b_in_dir, year)
        l2b_csv.to_csv('l2b_2019.csv')
