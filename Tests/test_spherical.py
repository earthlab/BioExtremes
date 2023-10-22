import numpy as np
import matplotlib.pyplot as plt

from Spherical.arc import Arc, Geodesic, PolyLine
from Spherical import numerics
import Spherical.functions as fn


def uniform_sample(n):
    """Uniformly sample latitudes and longitudes"""
    lons = np.random.rand(n) * 360 - 180
    lats = []
    while len(lats) < n:
        lat = np.random.rand() * 180 - 90
        if np.random.rand() < fn.cosd(lat):
            lats.append(lat)
    return np.array([lats, lons])


def plotarc(arc: Arc, **kwargs):
    latlon = arc(np.linspace(0, arc.length(), 500))
    plt.scatter(latlon[1], latlon[0], **kwargs)
    plt.xlim((-180, 180))
    plt.ylim((-90, 90))


def test_polyline_nearest():
    points = np.array([
        [45, -22, -22],
        [0, -90, 90]
    ])
    pl = PolyLine(points)
    res = 20
    latplot = np.linspace(-90, 90, res)
    lonplot = np.linspace(-180, 180, 2 * res)
    dists = []
    x = []
    y = []
    for lat in latplot:
        for lon in lonplot:
            _, d = pl.nearest((lat, lon))
            dists.append(d)
            x.append(lon)
            y.append(lat)
    plt.scatter(x, y, c=dists)
    plotarc(pl, color='red')
    plt.show()


def test_polyline_rejection():
    """Should never reject a triangle!"""
    for _ in range(500):
        try:
            points = uniform_sample(3)
            pl = PolyLine(points)
        except fn.SphericalGeometryError as sge:
            pl = PolyLine(points)   # try again for debugging purposes


def test_polyline_appearance():
    n_sides = 9
    n_tries = 0

    while True:
        try:
            n_tries += 1
            points = uniform_sample(n_sides)
            pl = PolyLine(points)
            plotarc(pl, s=1)
            plt.title(fr"PolyLine after {n_tries} random tries")
            plt.show()
            break
        except fn.SphericalGeometryError:
            continue


def test_nearest_to_pole():
    seed = np.random.randint(10000)
    np.random.seed(seed)
    failed = False
    for _ in range(500):
        lats = np.random.rand(3) * 180 - 90
        lons = np.random.rand(3) * 360 - 180
        geo = Geodesic((lats[0], lons[0]), (lats[1], lons[1]))
        tm, dm = geo.nearest((lats[2], lons[2]))
        geoplot = geo(np.linspace(0, geo.length()))
        dists = fn.anglelatlon((lats[2], lons[2]), geoplot)
        if (dists < dm - numerics.default_tol).any():
            plt.scatter(geoplot[1], geoplot[0], c=dists, s=5)
            plotarc(Geodesic(geo(tm), (90, 0)), c='black', s=1)
            plt.show()
            failed = True
            break
    if failed:
        raise Exception(fr"random seed = {seed}, nearest fails to return minumum distance")


def test_nearest_to_geo():
    geo = Geodesic((-49, -100), (56, 93))
    points = [(-33, 34), (88, -10), (22, 103), (-15, -135)]
    params = [geo.nearest(p)[0] for p in points]
    nearest = [geo(t) for t in params]
    geos = [Geodesic(p, n) for p, n in zip(points, nearest)]
    plotarc(geo, c='red', s=1)
    for g in geos:
        plotarc(g, c='black', s=1)
    plt.show()


def test_geodesic_appearance():
    """Visual test; user eyeballs a Cylindrical projection of geodesics."""
    p0 = (90, 0)
    p1 = (-89, 0)
    geo01 = Geodesic(p0, p1)        # most of the prime meridian
    p2 = (45, 20)
    p3 = (45, -160)
    geo23 = Geodesic(p2, p3)        # this geodesic passes through the North Pole across date line
    p4 = (-74, -16)
    p5 = (77, 111)
    geo45 = Geodesic(p4, p5)        # just a pretty random one
    p6 = (0, 30)
    p7 = (0, -163)
    geo67 = Geodesic(p6, p7)        # part of the equator crossing date line
    p8 = (-60, 130)
    p9 = (-60, -20)
    geo89 = Geodesic(p8, p9)        # near pole
    pa = (-30, 140)
    pb = (-30, 140)
    geoab = Geodesic(pa, pb)        # single point

    """PLOT CURVES"""

    for geoij, color, label in [
        (geo01, 'red', 'prime meridian'),
        (geo23, 'orange', 'through pole'),
        (geo45, 'green', 'random'),
        (geo67, 'blue', 'partial equator'),
        (geo89, 'purple', 'near pole'),
        (geoab, 'black', 'single point')
    ]:
        plotarc(geoij, s=1, c=color, label=label)

    """PLOT INTERSECTIONS"""

    geos = [geo01, geo23, geo45, geo67, geo89, geoab]
    intersections = []
    for i in range(5):
        for j in range(i + 1, 6):
            inter = geos[i].intersections(geos[j])
            if inter is not None:
                intersections.append(inter)
    intersections = np.hstack(intersections)
    plt.scatter(intersections[1], intersections[0], label="intersections", marker='*', s=80)

    plt.legend()
    plt.show()


