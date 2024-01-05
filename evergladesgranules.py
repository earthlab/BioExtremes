from datetime import date
from concurrent import futures

import numpy as np
import json
from Spherical.arc import Polygon
from GEDI.granuleconstraint import RegionGC
from GEDI.api import L2AAPI

import matplotlib.pyplot as plt


"""
Create an L2AAPI object to access the granules' metadata. This initialization 
will fail if the credentials in BEX_USER and BEX_PWD are invalid.
"""
api = L2AAPI()

"""
Create a granuleconstraint.GranuleConstraint functor which excludes granules outside 
the polygonal national park boundary. Note that the polygon is described in a json 
file with a local path.
"""
with open('/Users/fcseidl/EarthLab-local/everglades-national-park_225.geojson') as f:
  gj = json.load(f)
points = np.array(gj['features'][0]['geometry']['coordinates'][0]).T
points[0], points[1] = points[1], points[0].copy()
points = np.fliplr(points)
poly = Polygon(points)
granuleconstraint = RegionGC(poly, api)

"""
Plot the outline of the park.
"""
latlon = poly(np.linspace(0, poly.length(), 500))
plt.plot(latlon[1], latlon[0])
plt.show()

"""
Obtain an iterator over every L2A file in the GEDI archive with the '.xml' 
extension from January 2020.
"""
urls = api.urls_in_date_range(
    t_start=date(2020, 1, 1),
    t_end=date(2020, 1, 31),
    suffix='.xml'
)

"""
Finally, run through the iterator and print each url, along with an index and 
a boolean value indicating whether the granule intersects the everglades. Note 
that for the loop below to complete in under a day, map should be replaced 
with, e.g. a ThreadPoolExecutor.map call to exploit parallelization.
"""
print("index, accepted, url")
n = 1
for accept, url in map(granuleconstraint, urls):
    print(f"{n}, {accept}, {url}")
    n += 1