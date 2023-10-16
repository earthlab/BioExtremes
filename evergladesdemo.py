import os
from datetime import date
from multiprocessing import freeze_support

from GEDI.api import L2AAPI
from GEDI.download import downloadandfilterurls
from GEDI.shotconstraint import LatLonBox, Buffer
from GEDI.granuleconstraint import GranuleConstraint
from GMW import gmw


if __name__ == "__main__":
    freeze_support()

    api = L2AAPI()
    api.check_credentials()

    # get all h5 files with L2A data from summers 2020-23
    urls = api.urls_in_date_range(t_start=date(2020, 6, 20), t_end=date(2020, 9, 22), suffix='.h5')
    urls += api.urls_in_date_range(t_start=date(2021, 6, 20), t_end=date(2021, 9, 22), suffix='.h5')
    urls += api.urls_in_date_range(t_start=date(2022, 6, 21), t_end=date(2022, 9, 22), suffix='.h5')
    urls += api.urls_in_date_range(t_start=date(2023, 6, 21), t_end=date(2023, 9, 23), suffix='.h5')

    # use all full power beams
    beamnames = ['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011']
    # keep range of return heights
    keepobj = {
        "elev_lowestmode": "mean elevation",
        "elev_highestreturn": "highest return",
        "lat_lowestmode": "latitude",
        "lon_lowestmode": "longitude"
    }
    # contains national park
    bounds = LatLonBox(minlat=24.85, maxlat=25.89, minlon=-81.52, maxlon=-80.39)

    gmwdir = "/pl/active/earthlab/bioextremes/gmw_v3_2020/"
    #gmwdir = "/Users/fcseidl/Downloads/gmw_v3_2020/"
    print(f"Obtaining mangrove buffer from {gmwdir}...")
    tilenames = gmw.tiles_intersecting_region(gmwdir, bounds.spatial_predicate)
    points = gmw.mangrove_locations_from_tiles(gmwdir, tilenames)

    downloadandfilterurls(
        urls,
        beamnames,
        keepobj,
        keepevery=1,
        granuleselector=GranuleConstraint(bounds.spatial_predicate),    # TODO: put this predicate in geometry
        constraindf=Buffer(30, points),     # 30m resolution
        nproc=os.cpu_count(),
        csvdest="evergladesdata.csv"
    )
