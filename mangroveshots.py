
import re
import pandas as pd

from GMW import gmw
from GEDI.api import L2AAPI
from GEDI.shotconstraint import Buffer
from GEDI.download import downloadandfilterurls


# path to output of mangrovegranules.py
outfile = "/Users/fcseidl/EarthLab-local/BioExtremes/slurm-3597129.out"

# path to GMW 2020 folder
gmwdir = "/Users/fcseidl/EarthLab-local/BioExtremes/gmw_v3_2020/"


if __name__ == "__main__":
    print('Parsing urls of granules to download...')
    urls = []
    with open(outfile) as reader:
        exp = "[\d*], True, (.*).xml$"
        while True:
            line = reader.readline()
            if not line:
                break
            match = re.search(exp, line)
            if match is not None:
                urls.append(match.group(1))

    print("Checking authentication with https://urs.earthdata.nasa.gov...")
    api = L2AAPI()
    api.check_credentials()

    print('Loading GMW points into a Buffer (may take a while)...')
    tilenames = gmw.get_tile_names(gmwdir)
    points = gmw.get_mangrove_locations_from_tiles(gmwdir, tilenames)
    buffer = Buffer(30.0, points)   # 30 meter buffer (dataset is ~20 meter resolution)

    # this argument has us download latitude, longitude, and rh98.
    keepobj = pd.DataFrame({
        'key': ['lat_lowestmode', 'lon_lowestmode', 'rh'],
        'index': [None, None, 98],
        'name': ['latitude', 'longitude', 'rh98']
    })

    downloadandfilterurls(
        urls,
        api=api,
        beamnames=['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011'],     # full power beams
        keepobj=keepobj,
        keepevery=10,
        shotconstraint=buffer,
        nproc=2,
        csvdest='mangrove_rh98.csv'
    )
