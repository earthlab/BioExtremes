
import numpy as np
from sklearn.neighbors import BallTree
import matplotlib.pyplot as plt
import pickle

from GMW import gmw

print("Loading GMW points...")
gmwdir = "/Users/fcseidl/Downloads/gmw_v3_2020/"
tilenames = gmw.tiles_intersecting_region(gmwdir)
points = gmw.mangrove_locations_from_tiles(gmwdir, tilenames)
plt.scatter(points[::500, 1], points[::500, 0], s=1, c='black')
plt.show()

print("Forming tree...")
tree = BallTree(np.radians(points), metric="haversine")
with open("/Users/fcseidl/EarthLab-local/BioExtremes/gmw2020tree.pickle", "wb") as writer:
    pickle.dump(tree, writer)
print("Saved tree to " + "/Users/fcseidl/EarthLab-local/BioExtremes/gmw2020tree.pickle")
