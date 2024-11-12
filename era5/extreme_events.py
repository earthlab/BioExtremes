import collections
import os
import re
from datetime import datetime

from osgeo import gdal
import numpy as np
from tqdm import tqdm


class Base:
    def __init__(self, threshold_tif: str):
        self._threshold_raster = gdal.Open(threshold_tif)
        self._threshold_array = self._threshold_raster.ReadAsArray()
        self._file_date_pattern = r'(\d{10})_(\d{10})'

    def _calc_idf(self, bits: str, values: np.array, threshold: float, min_duration: int):
        # find EWEs
        regex = '0('  # start below threshold
        regex += ''.join(['1' for _ in range(min_duration)])  # remain above threshold for ndays
        regex += '*1)'  # any additional time above threshold counts too
        matches = list(re.finditer(regex, bits))

        return matches, 0, 0

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

    def create_idf_tif(self, in_dir: str, start_date: datetime, end_date: datetime, window: int, outfile: str,
                       threshold_functor, transform=lambda x: x):

        bits_dict = collections.defaultdict(str)
        value_dict = collections.defaultdict(list)

        sorted_files = []
        for file in os.listdir(in_dir):
            if not file.endswith('.tif'):
                continue
            match = re.search(self._file_date_pattern, file)

            if match:
                start_date_str = match.group(1)
                end_date_str = match.group(2)
                # Convert date strings to datetime objects
                file_start_date = datetime.strptime(start_date_str, "%Y%m%d%H")
                file_end_date = datetime.strptime(end_date_str, "%Y%m%d%H")
            else:
                continue

            if not (start_date <= file_start_date and end_date >= file_end_date):
                continue

            sorted_files.append(file)

        sorted_files = sorted(sorted_files,
                              key=lambda x: datetime.strptime(re.search(self._file_date_pattern, x).group(1), "%Y%m%d%H"))
        for file in tqdm(sorted_files, desc="Processing files"):
            raster = gdal.Open(os.path.join(in_dir, file))
            raster_array = raster.ReadAsArray()
            x_size, y_size = raster.RasterXSize, raster.RasterYSize

            # Progress bar for x_size loop
            for i in range(x_size):
                # Progress bar for y_size loop
                for j in range(y_size):
                    threshold = self._threshold_array[j, i]
                    # If the threshold is 0 then no threshold was calculated (not a mangrove location)
                    if threshold <= 0:
                        continue

                    bits_dict[(j, i)] += ''.join(['1' if threshold_functor(transform(v), threshold) else '0' for v in
                                                  raster_array[:, j, i]])
                    value_dict[(j, i)].extend([transform(v) for v in raster_array[:, j, i]])

            del raster
            del raster_array

        idft_dict = {}
        for k, v in tqdm(bits_dict.items(), desc='Calculating IDFT dict'):
            idft_dict[k] = self._calc_idf(v, np.array(value_dict[k]), self._threshold_array[k], window)

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
        print('Writing raster')
        self._write_raster(x_size, y_size, self._threshold_raster.GetGeoTransform(),
                           self._threshold_raster.GetProjection(), intensity_array, duration_array, frequency_array,
                           time_array, outfile)
        print('Done')


class Drought(Base):
    def __init__(self, threshold_tif: str):
        super().__init__(threshold_tif)

    def _calc_idf(self, bits: str, values: np.array, threshold: float, min_duration: int):
        matches, i, d = super()._calc_idf(bits, values, threshold, min_duration)

        t = 0
        for m in matches:
            event = values[m.start() + 1: m.end()]
            i_m = (threshold - event).sum()
            d_m = event.shape[0]

            if i_m > i:
                i = i_m
                t = m.end()
            if d_m > d:
                d = d_m
                t = m.end()

        # report time since last event, frequency, and maximum intensity / duration
        f = len(matches) / values.shape[0]

        # Each time step is one month, and we want duration and time since last event in years
        d /= 12
        t = (values.shape[0] - t) / 12

        # Each time step is one month, and we want frequency in events / year
        f *= 12

        return i, d, f, t

    def create_idf_tif(self, in_dir: str, start_date: datetime, end_date: datetime, window: int, outfile: str):
        super().create_idf_tif(in_dir, start_date, end_date, window, outfile, threshold_functor=lambda x, y: x <= y)


class Wind(Base):
    def __init__(self, threshold_tif: str):
        super().__init__(threshold_tif)

    def _calc_idf(self, bits: str, values: np.array, threshold: float, min_duration: int):
        matches, i, d = super()._calc_idf(bits, values, threshold, min_duration)

        t = 0
        for m in matches:
            event = values[m.start() + 1: m.end()]
            i_m = event.sum()
            d_m = event.shape[0]

            if i_m >= i:
                i = i_m
                t = m.end()

            if d_m >= d:
                d = d_m
                t = m.end()

        # report time since last event, frequency, and maximum intensity / duration
        f = (len(matches) / values.shape[0])
        f *= (4 * 365)  # Each time step is 6 hours, we want frequency in events / year

        d /= (4 * 365)  # Each time step is 6 hours, we want duration in years
        t = (values.shape[0] - t) / (4 * 365)  # Each time step is 6 hours, we want time since last event in years

        return i, d, f, t

    @staticmethod
    def _convert_era5_wind_speed_to_ibtracs(era5_speed: float) -> float:
        mps2kts = 1.94384
        m, b = 0.826599091061478, 13.383383250900929

        return ((era5_speed * mps2kts * m) + b) / mps2kts

    def create_idf_tif(self, in_dir: str, start_date: datetime, end_date: datetime, window: int, outfile: str):
        super().create_idf_tif(in_dir, start_date, end_date, window, outfile, threshold_functor=lambda x, y: x > y,
                               transform=self._convert_era5_wind_speed_to_ibtracs)
