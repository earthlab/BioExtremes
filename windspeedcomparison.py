"""
This script performs a comparison between maximum wind speeds from different storms as reported in IBTrACS and ERA5
datasets.
"""

import cdsapi
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import re
from urllib.request import urlopen
import xarray as xr
from tqdm import tqdm

from Spherical.functions import addtolon


mps2kts = 1.94384
savepath = "/Users/fcseidl/EarthLab-local/BioExtremes/WindComparisonBasins.csv"
np.random.seed(0)

# IBTrACS data where max wind and basin are recorded
ibt = pd.read_csv('/Users/fcseidl/Downloads/ibtracs.since1980.list.v04r00.csv')
ibt = ibt[1:]
ibt = ibt[ibt['WMO_WIND'] != ' ']
ibt = ibt[(ibt['BASIN'] == 'NA') | (ibt['BASIN'] == 'EP') | (ibt['BASIN'] == 'WP') | (ibt['BASIN'] == 'NI') |
          (ibt['BASIN'] == 'SI') | (ibt['BASIN'] == 'SP') | (ibt['BASIN'] == 'SA')]
nrows, _ = ibt.shape

# Copernicus client
client = cdsapi.Client(quiet=True)

# get data from N random storms
N = 600
idx = ibt.index[np.random.randint(0, nrows, N)]
basin = []
wmowind = []
era5wind = []
for i in tqdm(idx):
    basin.append(ibt['BASIN'][i])
    wmowind.append(float(ibt['WMO_WIND'][i]))
    lat = float(ibt['LAT'][i])
    lon = float(ibt['LON'][i])
    time = ibt['ISO_TIME'][i]
    m = re.search("(\d\d\d\d)-(\d\d)-(\d\d) (\d\d:\d\d):\d\d", time)
    params = {
        'product_type': 'reanalysis',
        'format': 'netcdf',
        'year': m.group(1),
        'month': m.group(2),
        'day': m.group(3),
        'time': m.group(4),
        'variable': 'instantaneous_10m_wind_gust',
        'area': [lat + 1, addtolon(lon, -1), lat - 1, addtolon(lon, 1)]
    }
    response = client.retrieve('reanalysis-era5-single-levels', params)
    with urlopen(response.location) as f:
        ds = xr.open_dataset(f.read())
        df = ds.to_dataframe().reset_index()
    '''
    # this will plot all readings from near the storm
    plt.scatter(df['longitude'], df['latitude'], c=df['i10fg'])
    plt.colorbar()
    plt.show()'''
    era5wind.append(df['i10fg'].max() * mps2kts)
basin = np.array(basin)
wmowind = np.array(wmowind)
era5wind = np.array(era5wind)
for b in np.unique(basin):
    plt.scatter(wmowind[basin == b], era5wind[basin == b], label=b)
plt.xlabel('IBTrACS wind speed (kts)')
plt.ylabel('ERA5 wind speed (kts)')
plt.legend()
plt.plot([0, 100], [0, 100])
plt.axis('equal')
plt.show()

savedata = pd.DataFrame({'ibtracs': wmowind, 'era5': era5wind, 'basin': basin})
print(f'Saving to {savepath}')
savedata.to_csv(savepath)






