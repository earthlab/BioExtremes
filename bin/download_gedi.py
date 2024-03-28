import os
import re
import pandas as pd
from argparse import ArgumentParser

from enums import GEDILevel
from gmw import gmw
from gedi.api import L2A, L2B, L1B
from gedi.shotconstraint import Buffer
from gedi.download import downloadandfilterurls
from bin.find_gedi_files_overlapping_mangroves import generate_overlap_output_file

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

# path to output of find_gedi_files_overlapping_mangroves.py
outfile = "L2A_gedi_files_overlapping_mangroves.csv"

# path to gmw 2020 folder
gmwdir = "gmw_v3_2020/"


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--file_level', type=str, help='Product level to download (L2A, L2B, L1B)',
                        required=True)
    args = parser.parse_args()

    file_level = GEDILevel[args.file_level]
    url_df = pd.read_csv(generate_overlap_output_file(file_level))
    urls = [u for i, u in enumerate(url_df['url']) if url_df['accepted'][i]]

    print("Checking authentication with https://urs.earthdata.nasa.gov...")

    if file_level == 'L2A':
        api = L2A()
    elif file_level == 'L2B':
        api = L2B()
    elif file_level == 'L1B':
        api = L1B()
    else:
        raise ValueError('Invalid file level')
    api.check_credentials()

    print('Loading gmw points into a Buffer (may take a while)...')
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
        keepevery=1,
        shotconstraint=buffer,
        nproc=4,
        outdir='mangrove_out'
    )
