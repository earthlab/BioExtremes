import numpy as np
import matplotlib.pyplot as plt

from Spherical.arc import Arc, Geodesic, Polygon, Parallel, BoundingBox
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


def test_bb_poly_intersection():
    poly = Polygon(np.array([
        [35, -10, -50, 0, 35],
        [-40, -10, 40, 25, 7]
    ]))
    bb = BoundingBox((0, -20), (50, -55))
    plotarc(poly, label='Polygon')
    plotarc(bb, label="Bounding Box")
    plt.show()


# TODO: parallel bug fixes
def test_parallel_intersects():
    par1 = Parallel(lat=0, lon0=0, lon1=-180)                   # western equator
    par2 = Parallel(lat=0, lon0=0, lon1=180)                    # eastern equator
    assert par1.intersections(par2).shape == (2, 2)
    geo1 = Geodesic((0, 0), (0, 100))                           # part of equator
    assert par1.intersections(geo1).shape == (2, 1)
    assert geo1.intersections(par2).shape == (2, 1)
    par3 = Parallel(lat=90, lon0=-180, lon1=180, crossdl=True)  # North Pole
    assert par3.intersections(par1) is None
    assert geo1.intersections(par3) is None
    assert par3.intersections(par3).shape == (2, 1)
    geo2 = Geodesic((70, -20), (40, 160))                       # thru pole
    assert geo2.intersections(par3).shape == (2, 1)
    par4 = Parallel(lat=-30, lon0=-15, lon1=15, crossdl=True)   # most of the way around
    geo3 = Geodesic((-10, 40), (-55, 65))                       # crosses only par4, only once
    assert par4.intersections(geo3).shape == (2, 1)
    assert geo3.intersections(par2) is None
    geo4 = Geodesic((-28, -140), (-28, 140))                    # crosses only par4, twice
    assert par4.intersections(geo4).shape == (2, 2)
    par5 = Parallel(lat=-55, lon0=60, lon1=70)                  # crosses tip of geo3
    assert par5.intersections(geo3).shape == (2, 1)
    par6 = Parallel(lat=-30, lon0=-10, lon1=10)                 # inside convex hull of geo4
    assert par6.intersections(geo4) is None


# TODO: parallel bug fixes
def test_parallel_appearance():
    par1 = Parallel(lat=60, lon0=-45, lon1=45)
    par2 = Parallel(lat=0, lon0=130, lon1=2)
    par3 = Parallel(lat=-30, lon0=-90, lon1=90, crossdl=True)
    par4 = Parallel(lat=-90, lon0=-180, lon1=180)
    for arc, lbl in [
        (par1, "arctic"),
        (par2, "equatorial"),
        (par3, "crosses IDL"),
        (par4, "south pole")
    ]:
        plotarc(arc, label=lbl)
    plt.ylim((-90, 90))
    plt.legend()
    plt.show()


def test_polyline_contains_appearance():
    points = np.array([
        [45, -22, -22],
        [0, -90, 90]
    ])
    pl = Polygon(points)
    res = 20
    latplot = np.linspace(-90, 90, res)
    lonplot = np.linspace(-180, 180, 2 * res)
    color = []
    x = []
    y = []
    # check grid of points
    for lat in latplot:
        for lon in lonplot:
            i = pl.contains((lat, lon))
            color.append('white' if i else 'black')
            x.append(lon)
            y.append(lat)
    # check ref p and antipode
    lat, lon = pl._refpt
    i = pl.contains((lat, lon))
    x.append(lon)
    y.append(lat)
    color.append('white' if i else 'black')
    lat, lon = -lat, (lon + 180) % 360 - 180
    i = pl.contains((lat, lon))
    x.append(lon)
    y.append(lat)
    color.append('white' if i else 'black')
    plt.scatter(x, y, c=color)
    plotarc(pl, color='red')
    plt.show()


def test_polyline_contains_angles():
    points = np.array([
        [45, -22, -22],
        [0, -90, 90]
    ])
    pl = Polygon(points)
    res = 6
    latplot = np.linspace(-90, 90, res)
    lonplot = np.linspace(-180, 180, 2 * res)
    color = []
    x = []
    y = []
    # check grid of points
    for lat in latplot:
        for lon in lonplot:
            i = pl.contains((lat, lon), method='angles')
            color.append('white' if i else 'black')
            x.append(lon)
            y.append(lat)
    # check ref p and antipode
    lat, lon = pl._refpt
    i = pl.contains((lat, lon))
    x.append(lon)
    y.append(lat)
    color.append('white' if i else 'black')
    lat, lon = -lat, (lon + 180) % 360 - 180
    i = pl.contains((lat, lon), method='angles')
    x.append(lon)
    y.append(lat)
    color.append('white' if i else 'black')
    plt.scatter(x, y, c=color)
    plotarc(pl, color='red')
    plt.show()


def test_polyline_nearest():
    points = np.array([
        [45, -22, -22],
        [0, -90, 90]
    ])
    pl = Polygon(points)
    res = 30
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
            pl = Polygon(points)
        except fn.SphericalGeometryException as sge:
            pl = Polygon(points)   # try again for debugging purposes


def test_polyline_appearance():
    n_sides = 6
    n_tries = 0

    while True:
        try:
            n_tries += 1
            points = uniform_sample(n_sides)
            pl = Polygon(points)
            break
        except fn.SphericalGeometryException:
            continue

    res = 20
    latplot = np.linspace(-90, 90, res)
    lonplot = np.linspace(-180, 180, 2 * res)
    color = []
    x = []
    y = []
    # check grid of points
    for lat in latplot:
        for lon in lonplot:
            i = pl.contains((lat, lon))
            color.append('white' if i else 'black')
            x.append(lon)
            y.append(lat)
    plt.scatter(x, y, c=color)
    plotarc(pl, color='red', s=1)
    plt.show()


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
    geoab = Geodesic(pa, pb)        # single p

    """PLOT CURVES"""

    for geoij, color, label in [
        (geo01, 'red', 'prime meridian'),
        (geo23, 'orange', 'through pole'),
        (geo45, 'green', 'random'),
        (geo67, 'blue', 'partial equator'),
        (geo89, 'purple', 'near pole'),
        (geoab, 'black', 'single p')
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


