import collections
import os
import re

from sklearn.neighbors import BallTree

from gmw import gmw
from osgeo import gdal
from datetime import datetime, timedelta
from gedi.shotconstraint import R_earth

from netCDF4 import Dataset
import numpy as np


PROJECT_DIR = os.path.dirname(__file__)


class ComputeThresholds:
    def __init__(self, gmw_dir: str, percentile: int = 95):
        self._gmw_dir = gmw_dir
        self._threshold_date_start = datetime(1979, 1, 1)
        self._threshold_date_end = datetime(2009, 1, 1)

        self._file_date_pattern = r'(\d{10})_(\d{10})'
        self._percentile = percentile

    @staticmethod
    def _convert_era5_wind_speed_to_ibtracs(era5_speed: float) -> float:
        mps2kts = 1.94384
        m, b = 0.826599091061478, 13.383383250900929

        return ((era5_speed * mps2kts * m) + b) / mps2kts

    def _calculate_mangrove_locations(self, era5_raster):
        geo_transform = era5_raster.GetGeoTransform()

        lons = [geo_transform[0] + i * geo_transform[1] for i in range(era5_raster.RasterXSize)]
        lats = [geo_transform[3] + j * geo_transform[5] for j in range(era5_raster.RasterYSize)]
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        lat_lon_pairs = np.vstack([lat_grid.ravel(), lon_grid.ravel()]).T
        lat_lon_pairs = np.radians(lat_lon_pairs)
        r = 27777.75 / R_earth
        tile_names = gmw.get_tile_names(self._gmw_dir)
        points = gmw.get_mangrove_locations_from_tiles(self._gmw_dir, tile_names)
        tree = BallTree(np.radians(points), leaf_size=15, metric='haversine')
        dist, _ = tree.query(lat_lon_pairs)

        return dist <= r

    @staticmethod
    def _write_raster(x_size, y_size, geo_transform, projection, output_array, outfile):
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(outfile, x_size, y_size, 1, gdal.GDT_Float32)
        output_dataset.SetGeoTransform(geo_transform)
        output_dataset.SetProjection(projection)

        output_dataset.GetRasterBand(1).WriteArray(output_array)

    def _calculate_value_dict(self, mangrove_locations, era5_dir, func=lambda x: x):
        value_dict = collections.defaultdict(list)
        for file in os.listdir(era5_dir):

            # Match the pattern in the filename
            match = re.search(self._file_date_pattern, file)

            if match:
                start_date_str = match.group(1)
                end_date_str = match.group(2)
                # Convert date strings to datetime objects
                start_date = datetime.strptime(start_date_str, "%Y%m%d%H")
                end_date = datetime.strptime(end_date_str, "%Y%m%d%H")
            else:
                continue

            if not file.endswith('.tif') or not (self._threshold_date_start <= start_date and end_date <=
                                                 self._threshold_date_end):
                continue

            try:
                raster = gdal.Open(os.path.join(era5_dir, file))
                a = raster.ReadAsArray()
                a = a.reshape(a.shape[0], -1)
            except AttributeError as e:
                print(f'Raster error with {file}, skipping')
                continue

            for i, mangrove_flag in enumerate(mangrove_locations):
                if mangrove_flag:
                    value_dict[i].extend(a[:, i])

        return value_dict

    # def compute_era5_total_precipitation_threshold(self, era5_dir, outfile: str):
    #     era5_raster = gdal.Open(os.path.join(era5_dir, os.listdir(era5_dir)[0]))
    #     mangrove_locations = self._calculate_mangrove_locations(era5_raster)
    #     value_dict = self._calculate_value_dict(mangrove_locations, era5_dir, func=)
    #
    #     projection = era5_raster.GetProjection()
    #     x_size, y_size = era5_raster.RasterXSize, era5_raster.RasterYSize
    #     geo_transform = era5_raster.GetGeoTransform()
    #     output_array = np.zeros(x_size * y_size)
    #     for k, v in value_dict.items():
    #         output_array[k] = np.percentile(v, self._percentile)
    #
    #     output_array = output_array.reshape((y_size, x_size))
    #     self._write_raster(x_size, y_size, geo_transform, projection, output_array, outfile)

    def compute_era5_wind_speed_threshold(self, era5_dir: str, outfile: str):
        era5_raster = gdal.Open(os.path.join(era5_dir, os.listdir(era5_dir)[0]))
        mangrove_locations = self._calculate_mangrove_locations(era5_raster)
        value_dict = self._calculate_value_dict(mangrove_locations, era5_dir)

        projection = era5_raster.GetProjection()
        x_size, y_size = era5_raster.RasterXSize, era5_raster.RasterYSize
        geo_transform = era5_raster.GetGeoTransform()
        output_array = np.zeros(x_size * y_size)
        for k, v in value_dict.items():
            output_array[k] = np.percentile([self._convert_era5_wind_speed_to_ibtracs(b) for b in v], self._percentile)

        output_array = output_array.reshape((y_size, x_size))
        self._write_raster(x_size, y_size, geo_transform, projection, output_array, outfile)
