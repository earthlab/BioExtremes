import numpy as np
import matplotlib.pyplot as plt

from gedidownload import downloadandfilterurls
from gedishotconstraint import LonLatBox, Buffer
from gedigranuleconstraint import GEDIGranuleConstraint


def test_lonlatbox_across_idl():
    granule_urls = [
        "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146210921_O08224_01_T04774_02_003_01_V002.h5",
        "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146010156_O08211_02_T02527_02_003_01_V002.h5"
    ]
    shotconstraint = LonLatBox(minlon=179, maxlon=-179)    # crossing date line
    granuleconstraint = GEDIGranuleConstraint(shotconstraint.spatial_predicate)
    keepobj = {
        'lon_lowestmode': 'longitude',
        'quality_flag': 'quality_flag',
        'degrade_flag': 'degrade_flag'
    }
    data = downloadandfilterurls(
        granule_urls,
        ["BEAM0101"],
        keepobj,
        granuleselector=granuleconstraint,
        constraindf=shotconstraint,
        progess_bar=False
    )
    # all shots in bounding box
    assert ((data['longitude'] >= 179) | (data['longitude'] <= -179)).all()
    # all shots good quality
    assert (data['quality_flag'] == 1).all()
    # all shots not degraded
    assert (data['degrade_flag'] == 0).all()
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
    data = downloadandfilterurls(
        urls,
        ['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011'],
        keepobj={'lon_lowestmode': 'longitude', 'lat_lowestmode': 'latitude'},
        constraindf=Buffer(500000, cities)
    )
    plt.scatter([138.60], [-34.93], label='Adelaide')
    plt.scatter([153.03], [-27.47], label='Brisbane')
    plt.scatter(data['longitude'], data['latitude'], s=1)
    plt.legend()
    plt.show()
