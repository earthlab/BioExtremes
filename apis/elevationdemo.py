import os

from gedifilter import filterl2abeam, LonLatBox, GEDIShotConstraint, downloadandfilterl2a
from gedi import L2A

# import matplotlib.pyplot as plt

from datetime import date

if __name__ == "__main__":
    # june-august 2020
    l2aurls = L2A().urls_in_date_range(
        t_start=date(2020, 6, 1),
        t_end=date(2020, 8, 31),
        suffix='.h5'
    )
    # full power beams
    beamnames = ['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011']
    keepobj = {'elev_lowestmode': 'elevation', 'lon_lowestmode': 'longitude', 'lat_lowestmode': 'latitude'}
    # Colorado is a spherical rectangle
    cobounds = LonLatBox(minlon=-109.0467, maxlon=-102.0467, minlat=37, maxlat=41)

    downloadandfilterl2a(
        l2aurls,
        beamnames,
        keepobj,
        keepevery=1000,
        constraindf=cobounds,
        csvdest='COelevation.csv',
        nproc=os.cpu_count()
    )

    '''# simple demo
    beamnames = ['BEAM0101', 'BEAM0110']
    keepobj = {'elev_lowestmode': 'elevation', 'lon_lowestmode': 'longitude', 'lat_lowestmode': 'latitude'}
    keepevery = 5

    # three consecutive quarter-orbits, should give a continuous curve
    urls = ["https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/" + name for name in
            ['GEDI02_A_2020146180335_O08222_02_T03349_02_003_01_V002.h5',
             'GEDI02_A_2020146180335_O08222_03_T03349_02_003_01_V002.h5',
             'GEDI02_A_2020146180335_O08222_04_T03349_02_003_01_V002.h5']]
    df = downloadandfilterl2a(urls, beamnames, keepobj, keepevery, nproc=3)#, csvdest='/Users/fcseidl/EarthLab-local/BioExtremes/killed.csv')

    plt.scatter(df['longitude'], df['elevation'], s=1)
    plt.xlabel('longitude')
    plt.ylabel('elevation')
    plt.show()
    plt.scatter(df['latitude'], df['elevation'], s=1)
    plt.xlabel('latitude')
    plt.ylabel('elevation')
    plt.show()'''
