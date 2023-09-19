
from gedifilter import filterl2abeam, LonLatBox, GEDIShotConstraint, downloadandfilterl2a
import matplotlib.pyplot as plt

if __name__ == "__main__":
    beamnames = ['BEAM0101', 'BEAM0110']
    keepobj = {'elev_lowestmode': 'elevation', 'lon_lowestmode': 'longitude', 'lat_lowestmode': 'latitude'}
    keepevery = 5

    # three consecutive quarter-orbits, should give a continuous curve
    urls = ["https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/" + name for name in
            ['GEDI02_A_2020146180335_O08222_02_T03349_02_003_01_V002.h5',
             'GEDI02_A_2020146180335_O08222_03_T03349_02_003_01_V002.h5',
             'GEDI02_A_2020146180335_O08222_04_T03349_02_003_01_V002.h5']]
    df = downloadandfilterl2a(urls, beamnames, keepobj, keepevery, nproc=4,
                              csvdest='/Users/fcseidl/EarthLab-local/BioExtremes/killed.csv')

    plt.scatter(df['longitude'], df['elevation'], s=1)
    plt.xlabel('longitude')
    plt.ylabel('elevation')
    plt.show()
    plt.scatter(df['latitude'], df['elevation'], s=1)
    plt.xlabel('latitude')
    plt.ylabel('elevation')
    plt.show()
