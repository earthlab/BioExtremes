
'''import os
import sys

cwd = os.getcwd()
sys.path.insert(0, cwd[:-4] + 'source/')'''

from gedifilter import LonLatBox, filterl2abeam


def test_lonlatbox():
    granule_id = "GEDI02_A_2020146010156_O08211_01_T02527_02_003_01_V002"
    box = LonLatBox(minlon=-180)
    keepobj = {
        'lon_lowestmode': 'longitude',
        'quality_flag': 'quality_flag',
        'degrade_flag': 'degrade_flag'
    }
    data = filterl2abeam(
        "BEAM0101",
        keepobj,
        constraindf=box
    )
    assert (data['longitude'] > -180).all()
    assert (data['quality_flag'] == 1).all()
    assert (data['degrade_flag'] == 0).all()

