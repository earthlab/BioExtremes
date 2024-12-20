import os
import re
from typing import List

import numpy as np
import rasterio
from osgeo import gdal

from Spherical.arc import Polygon, BoundingBox


def get_tile_corners(tilename: str) -> np.ndarray:
    """
    Parse the corner coordinates (counterclockwise) from the tilename, e.g.
    "GMW_S38E146_2020_v3.tif" ->

    [[-38, -39, -39, -38],
    [146, 146, 147, 147]].
    """
    lat = re.search(r"[NS](\d+)[EW]", tilename)
    if lat.group(0).startswith('N'):
        lat = int(lat.group(1))
    else:
        lat = -int(lat.group(1))
    lon = re.search(r"[EW](\d+)_", tilename)
    if lon.group(0).startswith('E'):
        lon = int(lon.group(1))
    else:
        lon = -int(lon.group(1))
    return np.array([
        [lat, lat - 1, lat - 1, lat],
        [lon, lon, lon + 1, lon + 1]
    ])


def get_tile_names(gmwdir: str) -> list[str]:
    """
    Get the names of 1x1 degree tiles which intersect a region of interest.
    :param gmwdir: Path to directory of gmw archive data, e.g. "/location/of/gmw_v3_2020/"
    :param spatial_predicate: Boolean function of lat, lon defining region. Can be None.
    :return: List of tile geotiff files of interest, e.g. ["GMW_S38E146_2020_v3.tif", "GMW_S38E145_2020_v3.tif"]
    """
    result = []
    for tilename in os.listdir(gmwdir):
        if tilename.startswith('.'):
            continue
        result.append(tilename)
    return result


def get_mangrove_locations_from_tiles(gmwdir: str, tilenames: list[str]) -> np.ndarray:
    """
    Create an array containing the lat, lon locations of mangrove pixels in a list of gmw tiles.
    :param gmwdir: Path to gmw data directory, e.g. "/location/of/gmw_v3_2020/"
    :param tilenames: List of geotiff files of interest, e.g. ["GMW_S38E146_2020_v3.tif", "GMW_S38E145_2020_v3.tif"]
    :return: Array whose rows are [lat, lon] coordinates of mangrove locations
    """
    latitude = []
    longitude = []
    for tn in tilenames:
        img = rasterio.open(os.path.join(gmwdir, tn))
        mangroves = img.read(1)
        idx = np.argwhere(mangroves == 1)
        lats, lons = idx[:, 0], idx[:, 1]
        lons, lats = img.transform * (lons, lats)  # geotiff puts lon before lat
        latitude.append(lats)
        longitude.append(lons)
    latitude = np.hstack(latitude)
    longitude = np.hstack(longitude)
    return np.vstack([latitude, longitude]).T


def get_tiles(tilenames: list[str]) -> list[BoundingBox]:
    """Return a list of Bounding Boxes representing the 1x1 degree tiles containing mangroves."""
    return [Polygon(get_tile_corners(tn)) for tn in tilenames]
