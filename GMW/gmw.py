
import os
import re
from typing import Callable
import numpy as np
import rasterio

from geometry import gch_intersects_region      # TODO: don't use this


def tiles_intersecting_region(gmwdir: str, spatial_predicate: Callable[[tuple], bool] = None) -> list[str]:
    """
    Get the names of 1x1 degree tiles which intersect a region of interest.
    :param gmwdir: Path to directory of GMW archive data, e.g. "/location/of/gmw_v3_2020/"
    :param spatial_predicate: Boolean function of lat, lon defining region. Can be None.
    :return: List of tile geotiff files of interest, e.g. ["GMW_S38E146_2020_v3.tif", "GMW_S38E145_2020_v3.tif"]
    """
    result = []
    for tilename in os.listdir(gmwdir):
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
        corners = [[lat, lon], [lat - 1, lon], [lat - 1, lon + 1], [lat, lon + 1]]
        if spatial_predicate is None or gch_intersects_region(corners, spatial_predicate):
            result.append(tilename)
    return result


def mangrove_locations_from_tiles(gmwdir: str, tilenames: list[str]) -> np.ndarray:
    """
    Create an array containing the lat, lon locations of mangrove pixels in a list of GMW tiles.
    :param gmwdir: Path to GMW data directory, e.g. "/location/of/gmw_v3_2020/"
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
        lons, lats = img.transform * (lons, lats)   # geotiff puts lon before lat
        latitude.append(lats)
        longitude.append(lons)
    latitude = np.hstack(latitude)
    longitude = np.hstack(longitude)
    return np.vstack([latitude, longitude]).T


# small test for debugging
if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from GEDI.shotconstraint import LatLonBox

    gmwdir = "/Users/fcseidl/Downloads/gmw_v3_2020/"
    # contains everglades national park
    bounds = LatLonBox(minlat=24.85, maxlat=25.8899, minlon=-81.5183, maxlon=-80.3887)
    tilenames = tiles_intersecting_region(gmwdir, bounds.spatial_predicate)
    points = mangrove_locations_from_tiles(gmwdir, tilenames)

    plt.scatter(points[:, 1], points[:, 0])
    plt.show()
