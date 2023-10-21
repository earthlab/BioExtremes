import numpy as np
import matplotlib.pyplot as plt

from Geometry.spherical import Geodesic


def test_geodesic_appearance():
    """Visual test; user eyeballs a Mercator projection of geodesics."""
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

    def plotgeo(geo: Geodesic, c, lbl):
        lat0, lon0 = geo.p0
        lat1, lon1 = geo.p1
        plt.scatter([lon0, lon1], [lat0, lat1], c=c, label=lbl)
        latlon = geo(np.linspace(0, 1, 500))
        plt.scatter(latlon[1], latlon[0], s=1, c=c)

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
                intersections.append(inter[0])
    intersections = np.array(intersections)
    plt.scatter(intersections[:, 1], intersections[:, 0], label="intersections", marker='*', s=80)

    plt.legend()
    plt.show()

