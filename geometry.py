import numpy as np
from typing import Callable


sind = lambda x: np.sin(x * np.pi / 180)
cosd = lambda x: np.cos(x * np.pi / 180)
arctan2d = lambda opp, adj: np.arctan2(opp, adj) * 180 / np.pi
arcsind = lambda x: np.arcsin(x) * 180 / np.pi


def latlon2cart(lat, lon):
    """Return Cartesian coordinates of a point on the globe where distance units are Earth radius."""
    x = cosd(lat) * cosd(lon)
    y = cosd(lat) * sind(lon)
    z = sind(lat)
    return x, y, z


def cart2latlon(x, y, z):
    """Returns latitutude and longitude of a Cartesian point."""
    lon = arctan2d(y, x)
    lat = arcsind(z / np.sqrt(x ** 2 + y ** 2 + z ** 2))
    return lat, lon


class GlobalGeodesic:
    """
    A parameterization g of the geodesic between two vertices on the Earth, such that g(0) is the starting point and
    g(1) is the ending point. Returns lat, lon as a tuple.
    TODO: constant speed parameterization?
    """

    def __init__(self, start: tuple, end: tuple):
        """
        :param start: Starting coordinates
        :param end: Ending coordinates
        """
        lat0, lon0 = start
        lat1, lon1 = end
        # convert to Cartesian coordinates
        self._cart0 = np.array(latlon2cart(lat0, lon0))
        self._cart1 = np.array(latlon2cart(lat1, lon1))

    def __call__(self, t: float) -> tuple:
        # convex combination of Cartesian coordinates
        cart = (1 - t) * self._cart0 + t * self._cart1
        return cart2latlon(cart[0], cart[1], cart[2])


def gch_intersects_region(
        points: np.array,
        spatial_predicate: Callable[[tuple], bool],
        nsamp: int = 100,
        seed: int = 1
) -> bool:
    """
    Return true with high probability if the geodesically convex hull of a set of (lat, lon) vertices intersects a
    region. Return false if the intersection is empty.

    :param points: Each row is [lat, lon], in degrees.
    :param spatial_predicate: Boolean function of lat, lon which defines region.
    :param nsamp: Number of random samples to run. Higher nsamp reduces the false positive rate as well as compute time.
    :param seed: numpy random seed.
    """
    rng = np.random.default_rng(seed)
    for _ in range(nsamp):
        chosen = rng.choice(points, size=2, replace=False)
        gg = GlobalGeodesic(chosen[0], chosen[1])
        if spatial_predicate(*gg(rng.random())):
            return True
    return False


