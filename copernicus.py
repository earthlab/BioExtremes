import cdsapi
from datetime import datetime
from typing import List
import numpy as np


class SingleLevels:
    def __init__(self):
        self._copernicus_client = cdsapi.Client()

    def _download(self):
        pass

    def _generate_dates(self, start_date: datetime, end_date: datetime):
        date_requests = {}
        years = np.arange(start_date.year, end_date.year+1, 1)
        for year in years:
            if year == start_date.year:
                months = np.arange(start_date.month, 13 if end_date.year > start_date.year else end_date.month + 1)
            elif year == end_date.year:
                months = np.arange(1, end_date.month + 1, 1)
            else:
                months = np.arange(1, 13, 1)

            months = [f'{month:02d}' for month in months]
            days = [f'{day:02d}' for day in np.arange(1, 32, 1)]
            hours = [f'{hour:02d}:00' for hour in range(24)]

            if months in date_requests:
                date_requests[months].append((str(year), days, hours))

        return [{'year': [v[0]], 'month': k, 'day': v[1], 'time':  v[2]} for k, v in date_requests.items()]

    def download_wind_gusts(self, start_date: datetime, end_date: datetime, roi: List[float] = None):
        pass

