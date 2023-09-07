
from gedi import L2A
from gedifilter import filterl2a, LonLatBox
import matplotlib.pyplot as plt

'''link = "https://e4ftl01.cr.usgs.gov/GEDI/GEDI02_A.002/2020.05.25/GEDI02_A_2020146010156_O08211_04_T02527_02_003_01_V002.h5"
dest = "Users/fcseidl/Desktop/GEDI02_A_2020146010156_O08211_04_T02527_02_003_01_V002.h5"

L2A()._download((link, dest))'''

colnames = ['quality_flag', 'longitude', 'latitude', 'elev_lowestmode']
colkeys = ['BEAM0101/' + cn for cn in ['quality_flag', 'lon_lowestmode', 'lat_lowestmode', 'elev_lowestmode']]
h5file="Users/fcseidl/Desktop/GEDI02_A_2020146010156_O08211_04_T02527_02_003_01_V002.h5"
constraint = LonLatBox(minlon=12, maxlon=33)

df = filterl2a(h5file, colkeys, colnames, constraindf=constraint)

plt.scatter(df['longitude'], df['elev_lowestmode'], s=1)
plt.xlabel('longitude')
plt.ylabel('elevation')
plt.show()
