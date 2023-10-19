"""
This module implements a variety of spherical geometry algorithms.
"""

from abc import abstractmethod, ABC
import numpy as np


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


class Arc(ABC):
    """An abstract class providing the interface of an Arc on the sphere."""

    @abstractmethod
    def length(self) -> float:
        """Return the length of the Arc, in radii."""
        pass

    @abstractmethod
    def parameterization(self, t: float | np.ndarray) -> np.ndarray:
        """
        A constant-speed parameterization of the Arc taking values in the closed interval [0, 1].

        :param t: shape (,) or (n,)
        :return: lat, lon coordinates of parameterization, shape (2,) or (2, n)
        """
        pass

    @abstractmethod
    def ccwchange(self, point: tuple) -> float:
        """Return the counterclockwise angular length of the arc as viewed from a (lat, lon) point."""
        pass

    @abstractmethod
    def intersections(self, other, atol: float = 1e-10) -> np.ndarray:
        """
        Return a numpy array of the parameter values t at which this arc intersects another, up to an absolute
        tolerance. Note that this array may be empty.
        """
        pass

    @abstractmethod
    def nearest(self, point: tuple, atol: float = 1e-10) -> float:
        """Return the parameter t of the point on the Arc closest to a (lat, lon) point, up to an absolute tolerance."""
        pass


class Geodesic(Arc):
    """An Arc representing the shortest path between two points."""

    def __init__(self, p0: tuple, p1: tuple):
        self.p0 = np.array(p0)
        self.p1 = np.array(p1)
        self._xyz0 = latlon2xyz(p0)
        self._xyz1 = latlon2xyz(p1)
        self._angle = arccosd(self._xyz0 @ self._xyz1)
        axis = np.cross(self._xyz0, self._xyz1)
        self._orthonormal = np.cross(axis, self._xyz0)
        self._orthonormal /= np.linalg.norm(self._orthonormal)

    def length(self) -> float:
        return self._angle

    def parameterization(self, t: float | np.ndarray) -> np.ndarray:
        s = self._angle * t
        xyzt = np.outer(self._xyz0, cosd(s)) + np.outer(self._orthonormal, sind(s))
        return xyz2latlon(xyzt)

    def ccwchange(self, point: tuple) -> float:
        pass

    def intersections(self, other, atol: float = 1e-10) -> np.ndarray:
        pass

    def nearest(self, point: tuple, atol: float = 1e-10) -> float:
        pass



