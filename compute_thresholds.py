import os
from datetime import datetime, timedelta

from netCDF4 import Dataset
import numpy as np


PROJECT_DIR = os.path.dirname(__file__)


def convert_era5_wind_speed_to_ibtracs(era5_speed: float) -> float:
    mps2kts = 1.94384
    m, b = 0.826599091061478, 13.383383250900929

    return ((era5_speed * mps2kts * m) + b) / mps2kts


def compute_era5_wind_speed_threshold(percentile: int = 95) -> float:
    era5_dir = os.path.join(PROJECT_DIR, 'data', 'era5')
    epoch = datetime(1900, 1, 1)
    threshold_date_start = datetime(1979, 1, 1)
    threshold_date_end = datetime(2009, 1, 1)

    values = []
    for file in os.listdir(era5_dir):
        d = Dataset(os.path.join(era5_dir, file))

        for i, hour in enumerate(d['time'][:]):
            date = epoch + timedelta(hours=int(hour))
            if threshold_date_start <= date <= threshold_date_end:
                for wind_speed in d['i10fg'][i, :, :].flatten():
                    values.append(convert_era5_wind_speed_to_ibtracs(wind_speed))

    return np.percentile(values, percentile)


def compute_era5_total_precipitation_threshold(percentile: int = 95) -> float:
    era5_dir = os.path.join(PROJECT_DIR, 'data', 'era5')
    epoch = datetime(1900, 1, 1)
    threshold_date_start = datetime(1979, 1, 1)
    threshold_date_end = datetime(2009, 1, 1)

    values = []
    for file in os.listdir(era5_dir):
        d = Dataset(os.path.join(era5_dir, file))

        for i, hour in enumerate(d['time'][:]):
            date = epoch + timedelta(hours=int(hour))
            if threshold_date_start <= date <= threshold_date_end:
                for total_precipitation in d['tp'][i, :, :].flatten():
                    values.append(total_precipitation)

    return values
