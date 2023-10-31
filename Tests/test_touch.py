import matplotlib.pyplot as plt

from Spherical.arc import Polygon
from Spherical.neighbors import touchset, BallTree
from GMW import gmw
from Tests.test_arcs import plotarc
from GEDI.shotconstraint import LatLonBox   # TODO: when possible, use a Spherical.arc.BoundingBox

import numpy as np


# Polygons crudely representing states
kansas = Polygon(np.array([
    [40, 37, 37, 40],
    [-102, -102, -94, -94]
]))
florida = Polygon(np.array([
    [30.24, 29.57, 29.05, 27.83, 26.45, 25.18, 24.63, 24.59, 26.70, 30.69],
    [-87.67, -85.04, -82.80, -82.86, -82.20, -81.18, -82.95, -80.37, -79.95, -81.29]
]))


def test_touch_appearance():
    gmwdir = "/Users/fcseidl/Downloads/gmw_v3_2020/"
    bounds = LatLonBox(minlat=24.85, maxlat=25.89, minlon=-81.52, maxlon=-80.39)
    tilenames = gmw.get_tile_names(gmwdir, bounds.spatial_predicate)
    points = gmw.get_mangrove_locations_from_tiles(gmwdir, tilenames)
    tree = BallTree(np.radians(points))
    d2set = lambda p: np.radians(florida.distance(np.degrees(p)))
    touch, x = touchset(d2set, tree)
    plotarc(florida, s=1, color='green' if touch else 'red')
    d2set = lambda p: np.radians(kansas.distance(np.degrees(p)))
    touch, x = touchset(d2set, tree)
    plotarc(kansas, s=1, color='green' if touch else 'red')
    plt.scatter(points[::100, 1], points[::100, 0])
    plt.show()


