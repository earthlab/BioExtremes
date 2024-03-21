import os
import netCDF4 as nc
from typing import List
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.enums import Resampling
from rasterio.warp import reproject, Resampling


def numpy_array_to_raster(array, top_left, hours_from_epoch, output_file):
    # Example spatial information
    crs = 'EPSG:4326'  # Example CRS (WGS84)
    transform = from_origin(top_left[0], top_left[1], 0.25, 0.25)
    extent = (0, array.shape[1], array.shape[2], 0)  # Example extent (xmin, xmax, ymin, ymax)

    # Example metadata
    profile = {
        'driver': 'GTiff',
        'dtype': array.dtype,
        'count': array.shape[0],
        'height': array.shape[1],
        'width': array.shape[2],
        'crs': crs,
        'transform': transform
    }

    # Create GeoTIFF file
    with rasterio.open(output_file, 'w', **profile) as dst:
        for i in range(array.shape[0]):
            dst.write(array[i], indexes=i + 1)
            dst.update_tags(i + 1, EPOCH='1900-1-1')
            dst.update_tags(i + 1, HOURS_FROM_EPOCH=str(hours_from_epoch[i]))


def create_filtered_instantaneous_file(input_file: str, output_file: str, hours: List[int], variable: str = 'I10FG'):
    input_raster = nc.Dataset(input_file)

    hours_from_epoch = []
    data = []
    for i, initial_time in enumerate(input_raster['forecast_initial_time'][:]):
        for j, forecast_hour in enumerate(input_raster['forecast_hour'][:]):
            if forecast_hour in hours:
                hours_from_epoch.append(initial_time + forecast_hour)
                data.append(input_raster[variable][j, i, :])

    numpy_array_to_raster(np.array(data), (input_raster['longitude'][0], input_raster['latitude'][0]),
                          hours_from_epoch, output_file)

