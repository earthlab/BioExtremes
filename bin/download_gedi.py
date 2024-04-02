import os
import pandas as pd
from argparse import ArgumentParser

from enums import GEDILevel
from gmw import gmw
from gedi.api import L2A, L2B
from gedi.shotconstraint import Buffer
from gedi.download import download_and_filter_urls

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--file_level', type=str, help='Product level to download (L2A, L2B, L1B)',
                        required=True)
    parser.add_argument('--overlapping_file_csv', type=str,
                        help='Path to csv file containing overlapping GEDI granules')
    parser.add_argument('--gmw_dir', type=str,
                        help='Path to directory containing overlapping mangrove tif files')
    parser.add_argument('--out_dir', type=str, help='Directory to write the output files to')
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    overlapping_file_csv = args.overlapping_file_csv
    gmw_dir = args.gmw_dir

    file_level = GEDILevel[args.file_level]
    url_df = pd.read_csv(overlapping_file_csv)
    urls = [u.replace(".xml", "") for i, u in enumerate(url_df['url']) if url_df['accepted'][i]]

    print("Checking authentication with https://urs.earthdata.nasa.gov...")

    if file_level == GEDILevel.L2A:
        api = L2A()
        keep_obj = pd.DataFrame({
            'key': ['lat_lowestmode', 'lon_lowestmode', 'rh'],
            'index': [None, None, 98],
            'name': ['latitude', 'longitude', 'rh98']
        })

    elif file_level == GEDILevel.L2B:
        api = L2B()
        keep_obj = pd.DataFrame({
            'key': ['geolocation/latitude_bin0', 'geolocation/longitude_bin0', 'fhd_normal', 'pai'],
            'index': [None, None, None, None],
            'name': ['latitude', 'longitude', 'fhd', 'pai']
        })

    else:
        raise ValueError('Invalid file level')
    api.check_credentials()

    print('Loading gmw points into a Buffer (may take a while)...')
    tile_names = gmw.get_tile_names(gmw_dir)
    points = gmw.get_mangrove_locations_from_tiles(gmw_dir, tile_names)
    buffer = Buffer(30.0, points, file_level)   # 30 meter buffer (dataset is ~20 meter resolution)

    download_and_filter_urls(
        urls,
        api=api,
        beam_names=['BEAM0101', 'BEAM0110', 'BEAM1000', 'BEAM1011'],     # full power beams
        keep_obj=keep_obj,
        shot_constraint=buffer,
        keep_every=1,
        nproc=4,
        out_dir=args.out_dir
    )
