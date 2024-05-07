import collections
import os
import re
from typing import List
from datetime import datetime

from osgeo import gdal
import numpy as np


class Base:
    def __init__(self, threshold_tif: str):
        self._threshold_raster = gdal.Open(threshold_tif)
        self._threshold_array = self._threshold_raster.ReadAsArray()
        self._file_date_pattern = r'(\d{10})_(\d{10})'

    @staticmethod
    def _calc_idft(bits: str, values: np.array, threshold: float, min_duration: int):
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

        # report time since last event, frequency, and maximum intensity / duration
        i = 0. if not i else max(i)
        d = 0. if not d else max(d)

        f = len(matches) / values.shape[0]
        t = (len(bits) - matches[-1].end()) if matches else values.shape[0]

        return i, d, f, t

    @staticmethod
    def _write_raster(x_size, y_size, geo_transform, projection, intensity_array, duration_array, frequency_array,
                      time_array, outfile):
        driver = gdal.GetDriverByName('GTiff')
        output_dataset = driver.Create(outfile, x_size, y_size, 4, gdal.GDT_Float64)
        output_dataset.SetGeoTransform(geo_transform)
        output_dataset.SetProjection(projection)

        # Loop through each raster band and write the arrays
        for i, array in enumerate([intensity_array, duration_array, frequency_array, time_array], start=1):

            band = output_dataset.GetRasterBand(i)
            band.WriteArray(array)
            band.SetNoDataValue(-1.0)

        # Close the dataset
        output_dataset = None

    def create_idft_tif(self, in_dir: str, start_date: datetime, end_date: datetime, window: int, outfile: str,
                        transform=lambda x: x):

        bits_dict = collections.defaultdict(str)
        value_dict = collections.defaultdict(list)
        for file in os.listdir(in_dir):

            match = re.search(self._file_date_pattern, file)

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

            raster = gdal.Open(os.path.join(in_dir, file))
            raster_array = raster.ReadAsArray()
            x_size, y_size = raster.RasterXSize, raster.RasterYSize

            for i in range(x_size):
                for j in range(y_size):
                    threshold = self._threshold_array[j, i]

                    # If the threshold is 0 then no threshold was calculated (not a mangrove location)
                    if threshold <= 0:
                        continue

                    bits_dict[(j, i)] += ''.join(['1' if transform(v) > threshold else '0' for v in raster_array[:, j, i]])
                    value_dict[(j, i)].extend([transform(v) for v in raster_array[:, j, i]])

            del raster
            del raster_array

        idft_dict = {}
        for k, v in bits_dict.items():
            idft_dict[k] = self._calc_idft(v, np.array(value_dict[k]), self._threshold_array[k], window)

        x_size, y_size = self._threshold_raster.RasterXSize, self._threshold_raster.RasterYSize
        intensity_array = np.full((y_size, x_size), fill_value=-1.0)
        duration_array = np.full((y_size, x_size), fill_value=-1.0)
        frequency_array = np.full((y_size, x_size), fill_value=-1.0)
        time_array = np.full((y_size, x_size), fill_value=-1.0)
        for k, v in idft_dict.items():
            intensity_array[k] = v[0]
            duration_array[k] = v[1]
            frequency_array[k] = v[2]
            time_array[k] = v[3]

        self._write_raster(x_size, y_size, self._threshold_raster.GetGeoTransform(),
                           self._threshold_raster.GetProjection(), intensity_array, duration_array, frequency_array,
                           time_array, outfile)


class Precipitation(Base):
    def __init__(self, threshold_tif: str):
        super().__init__(threshold_tif)


class Wind(Base):
    def __init__(self, threshold_tif: str):
        super().__init__(threshold_tif)

    @staticmethod
    def _convert_era5_wind_speed_to_ibtracs(era5_speed: float) -> float:
        mps2kts = 1.94384
        m, b = 0.826599091061478, 13.383383250900929

        return ((era5_speed * mps2kts * m) + b) / mps2kts

    def create_idft_tif(self, in_dir: str, start_date: datetime, end_date: datetime, window: int, outfile: str):
        super().create_idft_tif(in_dir, start_date, end_date, window, outfile,
                                transform=self._convert_era5_wind_speed_to_ibtracs)
