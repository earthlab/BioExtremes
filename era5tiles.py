"""
This script downloads ERA5 measurements of the 10m instantaneous wind
speed and total precipitation from each 1x1 degree tile in the gmw 2020
dataset.
"""
import os.path

import cdsapi
from tqdm import tqdm
from concurrent import futures

from gmw import gmw

PROJECT_DIR = os.path.dirname(__file__)

gmw_dir = os.path.join(PROJECT_DIR, 'data', 'gmw_bahamas')
era5_dir = os.path.join(PROJECT_DIR, 'data', 'era5_bahamas')

nproc = os.cpu_count() - 1

# request in netcdf format at 6h resolution
shared_params = {
    'product_type': 'reanalysis',
    'format': 'netcdf',
    'variable': ['instantaneous_10m_wind_gust', 'total_precipitation'],
    # 'day': [
    #     '01', '02', '03',
    #     '04', '05', '06',
    #     '07', '08', '09',
    #     '10', '11', '12',
    #     '13', '14', '15',
    #     '16', '17', '18',
    #     '19', '20', '21',
    #     '22', '23', '24',
    #     '25', '26', '27'
    #     '28', '29', '30',
    #     '31',
    # ],
    # 'time': [
    #     '00:00', '06:00', '12:00', '18:00'
    # ],
    # 'month': [
    #     '01', '02', '03'
    #     '04', '05', '06',
    #     '07', '08', '09',
    #     '10', '11', '12',
    # ]
}

_70s = ['1978', '1979']
_80s = ['1980', '1981', '1982', '1983', '1984',
        '1985', '1986', '1987', '1988', '1989']
_90s = ['1990', '1991', '1992', '1993', '1994',
        '1995', '1996', '1997', '1998', '1999']
_00s = ['2000', '2001', '2002', '2003', '2004',
        '2005', '2006', '2007', '2008', '2009']
_10s = ['2010', '2011', '2012', '2013', '2014',
        '2015', '2016', '2017', '2018', '2019']
_20s = ['2020', '2021', '2022', '2023']

# get name of each tile (these will tell us the coordinates)
names = gmw.get_tile_names(gmw_dir)

# Copernicus client
client = cdsapi.Client(quiet=True)


# method to get data from each tile
def download_tile(name):
    corners = gmw.get_tile_corners(name)
    north = int(corners[0, 0])
    east = int(corners[1, 2])
    south = int(corners[0, 1])
    west = int(corners[1, 0])
    params = {'area': [north, west, south, east]}
    params.update(shared_params)
    # for years, daterange in zip(
    #         [_70s, _80s, _90s, _00s, _10s, _20s],
    #         ['_1978_1979', '_1980_1989', '_1990_1999',
    #          '_2000_2009', '_2010_2019', '_2020_2023']
    # ):
    for year in _70s + _80s + _90s + _00s + _10s + _20s:
        for month in ['01', '02', '03' '04', '05', '06', '07', '08', '09', '10', '11', '12']:
            for day in [
                '01', '02', '03',
                '04', '05', '06',
                '07', '08', '09',
                '10', '11', '12',
                '13', '14', '15',
                '16', '17', '18',
                '19', '20', '21',
                '22', '23', '24',
                '25', '26', '27'
                '28', '29', '30',
                '31'
            ]:
                target = os.path.join(era5_dir, 'ERA5_' + name[4:-12] + year + month + day + '.netcdf')
                params.update({'year': year})
                params.update({'month': month})
                params.update({'day': day})

                # os.path.exists would be fine here, but futures worries about its thread safety
                if not os.path.isfile(target):
                    print(f'Retrieving {target}')
                    client.retrieve(
                        'reanalysis-era5-single-levels-monthly-means', params, target
                    )


# download them all (this will be time-consuming)
# with futures.ThreadPoolExecutor(nproc) as executor:
#     list(tqdm(executor.map(download_tile, names), total=len(names)))
for name in names:
    download_tile(name)
