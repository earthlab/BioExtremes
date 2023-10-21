import numpy as np
import matplotlib.pyplot as plt

from Geometry.spherical import Geodesic, anglelatlon
from Geometry import numerics


def plotgeo(geo: Geodesic, c, lbl=""):
    # lat0, lon0 = geo.source
    # lat1, lon1 = geo.dest
    # plt.scatter([lon0, lon1], [lat0, lat1], c=c, label=lbl)
    latlon = geo(np.linspace(0, geo.length(), 500))
    plt.scatter(latlon[1], latlon[0], s=1, c=c)
    plt.xlim((-180, 180))
    plt.ylim((-90, 90))


def test_spa_appearance():
    # TODO: plot some SimplePiecewiseArcs--maybe SimplePiecewiseGeodesics?
    pass


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
        dists = anglelatlon((lats[2], lons[2]), geoplot)
        if (dists < dm - numerics.default_tol).any():
            plt.scatter(geoplot[1], geoplot[0], c=dists, s=5)
            plotgeo(Geodesic(geo(tm), (90, 0)), c='black')
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
    plotgeo(geo, c='red')
    for g in geos:
        plotgeo(g, c='black')
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
        plotgeo(geoij, color, label)

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


