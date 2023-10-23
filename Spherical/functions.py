"""This module contains several functions useful for spherical geometry."""

import numpy as np


class SphericalGeometryException(Exception):
    """Exception thrown by spherical geometry routines."""
    def __init__(self, message: str):
        super().__init__(message)


# trig in degrees
sind = lambda x: np.sin(x * np.pi / 180)
cosd = lambda x: np.cos(x * np.pi / 180)
arctan2d = lambda opp, adj: np.arctan2(opp, adj) * 180 / np.pi
arcsind = lambda x: np.arcsin(x) * 180 / np.pi
arccosd = lambda x: np.arccos(x) * 180 / np.pi


def latlon2xyz(coords: tuple | np.ndarray) -> np.ndarray:
    """
    :param coords: coordinates to convert to Cartesian, shape (2,) or (2, n)
    :return: converted coordinates on unit sphere, shape (3,) or (3, n)
    """
    lat, lon = coords
    x = cosd(lat) * cosd(lon)
    y = cosd(lat) * sind(lon)
    z = sind(lat)
    return np.array([x, y, z])


def xyz2latlon(xyz: tuple | np.ndarray) -> np.ndarray:
    """
    :param xyz: coordinates to convert to lat/lon, shape (3,) or (3, n)
    :return: converted coordinates, shape (2,) or (2, n)
    """
    x, y, z = xyz
    lon = arctan2d(y, x)
    lat = arcsind(z / np.sqrt(x ** 2 + y ** 2 + z ** 2))
    return np.array([lat, lon])


def anglexyz(xyz0: np.ndarray, xyz1: np.ndarray) -> np.ndarray | float:
    """
    Compute the angle in degrees between two 3d vectors using the cosine formula. Supports shape combinations
    (3,) and (3,); (3,) and (3, n); and (3, n) and (3, n); but not (3, n) and (3,).
    """
    p0 = xyz2latlon(xyz0)
    p1 = xyz2latlon(xyz1)
    return anglelatlon(p0, p1)


def anglelatlon(p0: tuple | np.ndarray, p1: tuple | np.ndarray) -> float | np.ndarray:
    """
    Compute the angle in degrees between two unit vectors in (lat, lon) spherical coordinates. Supports shape
    combinations (2,) and (2,); (2,) and (2, n); and (2, n) and (2, n); but not (2, n) and (2,).
    """
    lat0, lon0 = p0
    lat1, lon1 = p1
    h2 = sind((lat1 - lat0) / 2.) ** 2 + cosd(lat1) * cosd(lat0) * sind((lon1 - lon0) / 2.) ** 2
    return 2 * arcsind(np.sqrt(h2))

