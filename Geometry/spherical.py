"""
This module implements a variety of spherical geometry algorithms.
"""

from abc import abstractmethod, ABC
import numpy as np

from Geometry import numerics


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
    return arccosd(xyz0 @ xyz1)


def anglelatlon(p0: np.ndarray, p1: np.ndarray) -> np.ndarray | float:
    """
    Compute the angle in degrees between two unit vectors in (lat, lon) spherical coordinates. Supports shape
    combinations (2,) and (2,); (2,) and (2, n); and (2, n) and (2, n); but not (2, n) and (2,)."""
    xyz0 = latlon2xyz(p0)
    xyz1 = latlon2xyz(p1)
    return anglexyz(xyz0, xyz1)


class Arc(ABC):
    """An abstract class providing the interface of an Arc on the sphere."""

    @abstractmethod
    def length(self) -> float:
        """Return the length of the Arc, in degrees."""
        pass

    @abstractmethod
    def _xyz(self, t: float | np.ndarray) -> np.ndarray:
        """The Cartesian coordinates of the parameterized curve."""
        pass

    def __call__(self, t: float | np.ndarray) -> np.ndarray:
        """
        A constant-speed parameterization of the Arc taking values in the closed interval [0, 1].

        :param t: shape (,) or (n,)
        :return: lat, lon coordinates of parameterization, shape (2,) or (2, n)
        """
        xyzt = self._xyz(t)
        return xyz2latlon(xyzt)

    @abstractmethod
    def intersections(self, other, atol: float = numerics.default_tol) -> np.ndarray:
        """
        Return a numpy array of the parameter values t at which this arc intersects another, up to a tolerance.
        Note that this array may be empty.

        :type other: Arc
        :param other: Another Arc to intersect.
        :param atol: Error tolerance, in degrees.
        :return: The array of intersections, with shape (2, n), or None if no intersections occur.
        """
        pass

    @abstractmethod
    def nearest(self, point: tuple, atol: float = numerics.default_tol) -> tuple[float]:
        """
        Nearest-point calculation.

        :param point: query point (lat, lon)
        :param atol: error tolerance
        :return: t, d, where t is the parameter value of the nearest point, and d is the distance in radii to the
                    nearest point.
        """
        pass


class Geodesic(Arc):
    """An Arc representing the shortest path between two points."""

    def __init__(self, p0: tuple, p1: tuple, _warn=True):
        self.p0 = np.array(p0)
        self.p1 = np.array(p1)
        self._xyz0 = latlon2xyz(p0)
        xyz1 = latlon2xyz(p1)
        self._angle = anglexyz(self._xyz0, xyz1)
        if _warn and self._angle >= 180 - numerics.default_tol:
            raise RuntimeWarning("Geodesics defined by near-antipodal points are numerically unstable.")
        self._axis = np.cross(self._xyz0, xyz1)
        self._axis /= np.linalg.norm(self._axis)
        self._orthonormal = np.cross(self._axis, self._xyz0)
        self._orthonormal /= np.linalg.norm(self._orthonormal)
        # slightly change destination based on numerical error
        self.p1 = self(1)

    def length(self) -> float:
        return self._angle

    def _xyz(self, t: float | np.ndarray) -> np.ndarray:
        s = self._angle * t
        if isinstance(s, float):
            return self._xyz0 * cosd(s) + self._orthonormal * sind(s)
        return np.outer(self._xyz0, cosd(s)) + np.outer(self._orthonormal, sind(s))

    def _intersectsgc(self, gc, atol) -> tuple | None:
        """
        Return where this geodesic intersects the great circle containing another geodesic gc.

        :type gc: Geodesic
        """
        def anglefromgc(t):
            xyz = self._xyz(t)
            return xyz @ gc._axis
        tint = numerics.bisection(anglefromgc, atol=atol)
        if tint is not None:
            return self(tint)

    def intersections(self, other, atol: float = numerics.default_tol) -> np.ndarray:
        if isinstance(other, Geodesic):
            p0 = self._intersectsgc(other, atol / (2 * np.pi))
            if p0 is None:
                return
            p1 = other._intersectsgc(self, atol / (2 * np.pi))
            if p1 is None:
                return
            geo = Geodesic(p0, p1, _warn=False)
            if geo.length() < atol:
                return np.array([geo(0.5)]).T     # return midpoint of path between intersections
            return
        raise NotImplementedError(fr"Cannot compute intersections between Geodesic and {type(other)}")

    def nearest(self, point: tuple, atol: float = numerics.default_tol) -> tuple[float]:
        xyz = latlon2xyz(point)

        def distance(t):
            xyzt = self._xyz(t)
            return anglexyz(xyz, xyzt)

        # NOTE: golden section search returns a global minimizer here,
        # even though the distance may have two local minima!
        return numerics.goldensection(distance, atol=atol / self._angle)    # error in t magnified in d by self._angle




