import os
from datetime import date

from GEDI.api import L2AAPI
from GEDI.download import downloadandfilterurls
from GEDI.shotconstraint import LatLonBox, Buffer
from GEDI.granuleconstraint import GranuleConstraint

# get all h5 files with L2A data from 2020 through 2022
urls = L2AAPI().urls_in_date_range(
    t_start=date(2020, 1, 1),
    t_end=date(2022, 12, 31),
    suffix='.h5'
)
# use all full power beams
beamnames = ['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011']
# keep range of return heights
keepobj = {
    "elev_lowestmode": "mean elevation", "elev_highestreturn": "highest return"
}
# approximate state border
cobounds = LatLonBox(minlon=-109.0467, maxlon=-102.0467, minlat=37, maxlat=41)
# city locations
points = [
    [40.015, -105.27],  # Boulder
    [39.74, -105.00],   # Denver
    [38.84, -104.82],   # Colorado Springs
    [39.48, -106.04],   # Breckenridge
    [39.06, -108.55],   # Grand Junction
    [38.09, -102.62],   # Lamar
]

downloadandfilterurls(
    urls,
    beamnames,
    keepobj,
    granuleselector=GranuleConstraint(cobounds.spatial_predicate),    # TODO: put this predicate in geometry
    constraindf=Buffer(50000, points),     # 50 km resolution
    nproc=os.cpu_count(),
    csvdest="cityelevations.csv"
)

