import os
from datetime import date

from GEDI.api import L2AAPI
from GEDI.download import downloadandfilterurls
from GEDI.shotconstraint import LatLonBox, Buffer
from GEDI.granuleconstraint import GranuleConstraint
from GMW import gmw

# get all h5 files with L2A data from 2020
urls = L2AAPI().urls_in_date_range(
    t_start=date(2020, 1, 1),
    t_end=date(2020, 12, 31),
    suffix='.h5'
)
# use all full power beams
beamnames = ['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011']
# keep range of return heights
keepobj = {
    "elev_lowestmode": "mean elevation", "elev_highestreturn": "highest return"
}
# contains national park
bounds = LatLonBox(minlat=24.85, maxlat=25.8899, minlon=-81.5183, maxlon=-80.3887)
# mangrove locations
gmwdir = "gmw_v3_2020"
tilenames = gmw.tiles_intersecting_region(gmwdir)
points = gmw.mangrove_locations_from_tiles(gmwdir, tilenames)

downloadandfilterurls(
    urls,
    beamnames,
    keepobj,
    granuleselector=GranuleConstraint(bounds.spatial_predicate),    # TODO: put this predicate in geometry
    constraindf=Buffer(30, points),     # 30m resolution
    nproc=os.cpu_count(),
    csvdest="evergladesdata.csv"
)


