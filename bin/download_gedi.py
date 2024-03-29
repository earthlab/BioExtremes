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


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--file_level', type=str, help='Product level to download (L2A, L2B, L1B)',
                        required=True)
    parser.add_argument('--overlapping_file_csv', type=str,
                        help='Path to csv file containing overlapping GEDI granules')
    parser.add_argument('--gmw_dir', type=str,
                        help='Path to directory containing overlapping mangrove tif files')
    args = parser.parse_args()

    overlapping_file_csv = args.overlapping_file_csv
    gmw_dir = args.gmw_dir

    file_level = GEDILevel[args.file_level]
    url_df = pd.read_csv(generate_overlap_output_file(file_level))
    urls = [u.replace(".xml", "") for i, u in enumerate(url_df['url']) if url_df['accepted'][i]]

    print("Checking authentication with https://urs.earthdata.nasa.gov...")

    if file_level == GEDILevel.L2A:
        api = L2A()
    elif file_level == GEDILevel.L2B:
        api = L2B()
    elif file_level == GEDILevel.L1B:
        api = L1B()
    else:
        raise ValueError('Invalid file level')
    api.check_credentials()

    print('Loading gmw points into a Buffer (may take a while)...')
    tilenames = gmw.get_tile_names(gmw_dir)
    points = gmw.get_mangrove_locations_from_tiles(gmw_dir, tilenames)
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
