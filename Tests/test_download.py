import numpy as np
import matplotlib.pyplot as plt
import pickle

import pandas as pd

from gedi.download import downloadandfilterurls
from gedi.shotconstraint import LatLonBox, Buffer
from gedi.api import L2A


def test_lonlatbox_across_idl():
    granule_urls = [
        "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146210921_O08224_01_T04774_02_003_01_V002.h5"
    ]
    shotconstraint = LatLonBox(minlon=179, maxlon=-179)    # crossing date line
    keepobj = pd.DataFrame({
        'key': ['lon_lowestmode', 'quality_flag', 'rh', 'rh'],
        'name': ['longitude', 'quality_flag', 'rh25', 'rh75'],
        'index': [None, None, 25, 75]
    })
    data = downloadandfilterurls(
        granule_urls,
        L2A(),
        ["BEAM0101"],
        keepobj,
        shotconstraint=shotconstraint,
        progess_bar=False
    )
    # all shots in bounding box
    assert ((data['longitude'] >= 179) | (data['longitude'] <= -179)).all()
    # all shots good quality
    assert (data['quality_flag'] == 1).all()
    # only shots from first granule kept (second is outside bounds)
    assert (data['granule_id'] == 'GEDI02_A_2020146210921_O08224_01_T04774_02_003_01_V002').all()
    # all shots from the same beam (only 0101 was requested)
    assert (data['beam'] == 'BEAM0101').all()


# TODO: make this a pass/fail test rather than visual inspection?
def test_buffered_cities():
    urls = [
        'https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146023448_O08212_01_T03798_02_003_01_V002.h5']
    cities = np.array([
        [-34.93, 138.60],   # Adelaide
        [-27.47, 153.03]    # Brisbane
    ])
    keepobj = pd.DataFrame({
        'key': ['lon_lowestmode', 'lat_lowestmode'],
        'index': [None, None],
        'name': ['longitude', 'latitude']
    })
    data = downloadandfilterurls(
        urls,
        L2A(),
        ['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011'],
        keepobj=keepobj,
        shotconstraint=Buffer(500000, cities),
        nproc=2
    )
    plt.scatter([138.60], [-34.93], label='Adelaide')
    plt.scatter([153.03], [-27.47], label='Brisbane')
    plt.scatter(data['longitude'], data['latitude'], s=1)
    plt.legend()
    plt.show()
