import collections
import os
import re
from typing import List
from datetime import datetime

from osgeo import gdal
import numpy as np


class Precipitation:
    def __init__(self, threshold_tif: str):
        self._threshold_raster = gdal.Open(threshold_tif)
        self._threshold_array = self._threshold_raster.ReadAsArray()
        self._file_date_pattern = r'(\d{10})_(\d{10})'

    @staticmethod
    def _calc_idf(bits: str, values: np.array, threshold: float, min_duration: int):
        # find EWEs
        regex = '0('  # start below threshold
        regex += ''.join(['1' for _ in range(min_duration)])  # remain above threshold for ndays
        regex += '*1)'  # any additional time above threshold counts too
        matches = list(re.finditer(regex, bits))

        # compute intensity and duration of each EWE
        i = []
        d = []
        for m in matches:
            event = values[m.start() + 1: m.end()]
            i.append((event - threshold).sum())
            d.append(event.shape[0])

        print(i, d)

        # report maximum intensity and duration
        i = 0. if not i else max(i)
        d = 0. if not d else max(d)

        f = len(matches) / values.shape[0]
        print(i, d, f)

        return i, d, f

    @staticmethod
    def _write_raster(x_size, y_size, geo_transform, projection, intensity_array, duration_array, frequency_array,
                      outfile):
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(outfile, x_size, y_size, 3, gdal.GDT_Float32)
        output_dataset.SetGeoTransform(geo_transform)
        output_dataset.SetProjection(projection)

        output_dataset.GetRasterBand(1).WriteArray(intensity_array)
        output_dataset.GetRasterBand(2).WriteArray(duration_array)
        output_dataset.GetRasterBand(3).WriteArray(frequency_array)

    def create_idf_tif(self, in_dir: str, start_date: datetime, end_date: datetime, month_window: int, outfile: str):

        bits_dict = collections.defaultdict(str)
        value_dict = collections.defaultdict(list)
        for precipitation_file in os.listdir(in_dir):

            match = re.search(self._file_date_pattern, precipitation_file)

            if match:
                start_date_str = match.group(1)
                end_date_str = match.group(2)
                # Convert date strings to datetime objects
                file_start_date = datetime.strptime(start_date_str, "%Y%m%d%H")
                file_end_date = datetime.strptime(end_date_str, "%Y%m%d%H")
            else:
                continue

            if not (start_date <= file_start_date and end_date <= file_end_date):
                continue

            precipitation_raster = gdal.Open(os.path.join(in_dir, precipitation_file))
            precipitation_array = precipitation_raster.ReadAsArray()
            x_size, y_size = precipitation_raster.RasterXSize, precipitation_raster.RasterYSize

            for i in range(x_size):
                for j in range(y_size):
                    threshold = self._threshold_array[j, i]

                    # If the threshold is 0 then no threshold was calculated (not a mangrove location)
                    if threshold <= 0:
                        continue

                    bits_dict[(j, i)] += ''.join(['1' if v > threshold else '0' for v in precipitation_array[:, j, i]])
                    value_dict[(j, i)].extend(precipitation_array[:, j, i])

            del precipitation_raster
            del precipitation_array

        idf_dict = {}
        for k, v in bits_dict.items():
            idf_dict[k] = self._calc_idf(v, np.array(value_dict[k]), self._threshold_array[k], month_window)

        x_size, y_size = self._threshold_raster.RasterXSize, self._threshold_raster.RasterYSize
        intensity_array = np.zeros((y_size, x_size))
        duration_array = np.zeros((y_size, x_size))
        frequency_array = np.zeros((y_size, x_size))
        for k, v in idf_dict.items():
            intensity_array[k] = v[0]
            duration_array[k] = v[1]
            frequency_array[k] = v[2]

        self._write_raster(x_size, y_size, self._threshold_raster.GetGeoTransform(),
                           self._threshold_raster.GetProjection(), intensity_array, duration_array, frequency_array,
                           outfile)
