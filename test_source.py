
from gedifilter import LonLatBox, downloadandfilterl2aurls


def test_lonlatbox_across_idl():
    granule_urls = [
        "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146210921_O08224_01_T04774_02_003_01_V002.h5",
        "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146010156_O08211_02_T02527_02_003_01_V002.h5"
    ]
    box = LonLatBox(minlon=179, maxlon=-179)    # crossing date line
    keepobj = {
        'lon_lowestmode': 'longitude',
        'quality_flag': 'quality_flag',
        'degrade_flag': 'degrade_flag'
    }
    data = downloadandfilterl2aurls(
        granule_urls,
        ["BEAM0101"],
        keepobj,
        constraindf=box,
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

