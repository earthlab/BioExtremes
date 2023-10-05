import os

from gedifilter import filterl2abeam, LonLatBox, GEDIShotConstraint, downloadandfilterl2aurls
from gedi import L2A

import matplotlib.pyplot as plt

from datetime import date

if __name__ == "__main__":
    # 2020
    l2aurls = L2A().urls_in_date_range(
        t_start=date(2020, 1, 1),
        t_end=date(2020, 12, 31),
        suffix='.h5'
    )
    # full power beams
    beamnames = ['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011']
    keepobj = {'elev_lowestmode': 'elevation', 'lon_lowestmode': 'longitude', 'lat_lowestmode': 'latitude'}
    # Colorado is a spherical rectangle
    cobounds = LonLatBox(minlon=-109.0467, maxlon=-102.0467, minlat=37, maxlat=41)

    downloadandfilterl2aurls(
        l2aurls,
        beamnames,
        keepobj,
        keepevery=100,
        constraindf=cobounds,
        csvdest='COelevation.csv',
        nproc=os.cpu_count()
    )
