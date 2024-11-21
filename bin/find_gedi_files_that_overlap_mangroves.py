"""Save the names of granules containing gmw points."""
import os
from functools import partial
from argparse import ArgumentParser
from datetime import datetime
from concurrent import futures
import warnings

from gmw import gmw
import pandas as pd
from enums import GEDILevel
from gedi.api import L2A, L2B
from gedi.granuleconstraint import RegionGC, CompositeGC


warnings.filterwarnings("ignore")
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
nproc = os.cpu_count()


def save_progress(accepted, new_urls, filename):
    # Create a DataFrame from the lists
    df = pd.DataFrame({
        'accepted': accepted,
        'url': new_urls
    })
    # Save the DataFrame to a CSV file
    df.to_csv(filename, index=False)


def find_overlap(file_level: GEDILevel, start_date: datetime, end_date: datetime, gmw_dir: str, output_file: str):
    """
    Use the gmw.gmw module to obtain bounding boxes for each 1x1 degree cell of the global grid containing mangroves.
    """
    print("Loading bounding boxes of gmw tiles...")
    names = gmw.get_tile_names(gmw_dir)
    tiles = gmw.get_tiles(names)

    """
    Use the gedi.api module to connect to earthdata servers and obtain metadata for L2A granules. Other products, e.g. 
    L1B, can be handled similarly, but since we are only interested in granule metadata which is shared between 
    products, we won't do that here.
    """
    print("Checking authentication with https://urs.earthdata.nasa.gov...")

    if file_level == GEDILevel.L2A:
        api = L2A()
    elif file_level == GEDILevel.L2B:
        api = L2B()
    else:
        raise ValueError('Invalid file level')

    api.check_credentials()
    print('Credentials valid')

    checkpoint = output_file.replace('.csv', '_checkpoint.csv')
    accepted, new_urls = [], []
    if os.path.exists(checkpoint):
        checkpoint_df = pd.read_csv(checkpoint)
        accepted += list(checkpoint_df['accepted'])
        new_urls += list(checkpoint_df['url'])

    """
    The gedi.granuleconstraint module is used to determine which granules are of interest. In this case, we create a 
    composite constraint which accepts granules if and only if they intersect one of the mangrove cells obtained above. 
    The module is capable of constraining granules to arbitrary unions or intersections of polygons or bounding boxes.
    """
    constraint = CompositeGC(
        constraints=[RegionGC(tile, api) for tile in tiles],
        disjunction=True
    )

    """
    This gedi.api method gives an iterator over every (in this case, L2A) file in the gedi archive with a certain 
    extension from 2020. 
    """
    urls = api.urls_in_date_range(
        t_start=start_date,
        t_end=end_date,
        suffix='.xml'
    )

    """
    This block performs the brunt of the computation, which is why parallelism is employed here. As the loop runs, it 
    will print every granule with an associated index, a boolean value indicating if the granule passes the constraint 
    specified above, and the link to the granule's associated xml metadata file. Output can be redirected to store this 
    information permanently, so that it can be used to selectively download granules for shot-level subsetting. 
    Note that the loop will take a while to get going because ThreadPoolExecutor.map() unpacks the iterable up front.
    """
    save_interval = 1000
    with futures.ThreadPoolExecutor(nproc) as executor:
        partial_func = partial(constraint, existing_urls=new_urls)
        for i, (accept, url) in enumerate(executor.map(partial_func, urls)):
            if accept is not None:
                accepted.append(accept)
                new_urls.append(url)

                # Save progress at intervals
                print(i % save_interval == 0)
                if i > 0 and i % save_interval == 0:
                    print(f'saving progress to {checkpoint}')
                    save_progress(accepted, new_urls, checkpoint)

    if accepted and new_urls:
        save_progress(accepted,  new_urls, output_file)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--file_level', type=str, help='Product level to download (L2A, L2B)',
                        required=True, choices=['L2A', 'L2B'])
    parser.add_argument('--gmw_dir', type=str, help='Path to mangrove location files',
                        default=os.path.join(DATA_DIR, 'gmw_v3_2020'))
    parser.add_argument('--output_file', type=str, help='Path to output csv file')
    parser.add_argument('--start_date', type=str, help='Start date of overlap search in YYYY-MM-DD',
                        required=False)
    parser.add_argument('--end_date', type=str, help='End date of overlap search in YYYY-MM-DD',
                        required=False)
    args = parser.parse_args()

    if args.output_file is None:
        args.output_file = os.path.join(DATA_DIR, 'gedi', f'{args.file_level}_overlapping_gedi_files.csv')

    find_overlap(
        GEDILevel[args.file_level],
        datetime(2019, 4, 18) if args.start_date is None else datetime.strptime(
            args.start_date, '%Y-%m-%d'),
        datetime.today() if args.end_date is None else datetime.strptime(
            args.end_date, '%Y-%m-%d'),
        args.gmw_dir,
        args.output_file
    )
