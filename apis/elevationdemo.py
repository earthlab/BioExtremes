
from gedi import L2A
from gedifilter import filterl2abeam, LonLatBox, GEDIShotConstraint, downloadandfilterl2a
import matplotlib.pyplot as plt

'''link = "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146010156_O08211_04_T02527_02_003_01_V002.h5"
dest = "Users/fcseidl/Desktop/GEDI02_A_2020146010156_O08211_04_T02527_02_003_01_V002.h5"

L2A()._download((link, dest))'''

beamnames = ['BEAM0101', 'BEAM0110']
keepobj = {'elev_lowestmode': 'elevation', 'lon_lowestmode': 'longitude'}
constraint = GEDIShotConstraint()
# four consecutive quarter-orbits, should give continuous curve
urls = ["https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/" + name for name in
        ['GEDI02_A_2020146180335_O08222_02_T03349_02_003_01_V002.h5',
         'GEDI02_A_2020146180335_O08222_03_T03349_02_003_01_V002.h5',
         'GEDI02_A_2020146180335_O08222_04_T03349_02_003_01_V002.h5',
         'GEDI02_A_2020146193628_O08223_01_T00504_02_003_01_V002.h5']]
df = downloadandfilterl2a(urls, beamnames, keepobj, wdir='Users/fcseidl/EarthLab-local/BioExtremes/')

#datafile = "Users/fcseidl/Desktop/GEDI02_A_2020146010156_O08211_04_T02527_02_003_01_V002.h5"
#constraint = LonLatBox(minlon=12, maxlon=33)

#df = filterl2abeam(datafile, beamname, keepobj, constraindf=constraint)

plt.scatter(df['longitude'], df['elevation'], s=1)
plt.xlabel('longitude')
plt.ylabel('elevation')
plt.show()
