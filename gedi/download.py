"""
This module provides a single public method, downloadandfilterurls(), which allows users to download data from a list
of gedi granules, while specifying granule-level and shot-level constraints.
"""

from typing import Callable
import h5py
import pandas as pd
import os
from concurrent import futures
from tqdm import tqdm
import time

from gedi.api import GEDIAPI
from gedi.shotconstraint import ShotConstraint


def _subset_beam(
        granule,
        beam: str,
        keep_obj: pd.DataFrame,
        keep_every: int,
        constraint_df: ShotConstraint,
) -> pd.DataFrame:
    """
    Subset the data from a single beam from a granule, so that only shots meeting a constraint are kept.
    Beam name is added to the dataframe.
    """
    granule = h5py.File(granule, 'r')
    df = {}
    keys = list(keep_obj['key']) + constraint_df.get_keys()
    names = list(keep_obj['name']) + constraint_df.get_keys()
    indices = list(keep_obj['index']) + [None for _ in constraint_df.get_keys()]
    for key, name, idx in zip(keys, names, indices):
        try:
            obj = beam + '/' + key
            try:
                idx = int(idx)
                df[name] = granule[obj][()][::keep_every, int(idx)]
            except (ValueError, TypeError):  # idx cannot be cast to int
                df[name] = granule[obj][()][::keep_every]
        except KeyError:
            # TODO: what is happening? At least print the name of the file
            print(f'Download failed: could not receive data from {obj}')
            return
    df = pd.DataFrame(df)
    constraint_df(df)
    df.drop(columns=[col for col in names if not (col == keep_obj['name']).any()], inplace=True)
    # add beam name to df
    df['beam'] = [beam for _ in range(df.shape[0])]
    return df


def _subset_granule(
        granule,
        beam_names: list[str],
        keep_obj: pd.DataFrame,
        keep_every: int,
        constraint_df: ShotConstraint
) -> pd.DataFrame:
    """
    First parameter is a file-like object with data to filter. Subsequent parameters are the beamnames, keepobj,
    keepevery, and shotconstraint arguments as used by downloadandfilterl2aurls(). Return a dataframe with the filtered
    data, or nothing if no data is extracted.
    """
    frames = []
    for beamname in beam_names:
        df = _subset_beam(granule, beamname, keep_obj, keep_every=keep_every, constraint_df=constraint_df)
        if df is not None:
            frames.append(df)
    out_frame = pd.concat(frames, ignore_index=True)
    return out_frame


def _process_granule(args: tuple):
    """
    Filter multiple beams from a gedi granule. Inputs are taken in a single tuple for compatibility with
    multiprocessing.Pool.imap_unordered. Granule id is added to dataframe.

    :param args: Contains, in order, the remote url to the data, an appropriate GEDIAPI object to access that link,
                    then the beamnames, keepobj, keepevery, and shotconstraint arguments as used by
                    downloadandfilterl2aurls().
    :return: Filtered data from all beams. Return nothing if no data is extracted.
    """
    link, api, beam_names, keep_obj, keep_every, constraint_df, out_dir = args
    # download and filter large h5 file
    df = api.process_in_memory_file(
        link,
        _subset_granule,
        beam_names, keep_obj, keep_every, constraint_df
    )
    # add granule id to df
    istart = link.rindex('/') + 1
    iend = link.rindex('.')
    granule_id = link[istart:iend]
    df['granule_id'] = [granule_id for _ in range(df.shape[0])]
    print(f'Writing {link}')
    df.to_csv(os.path.join(out_dir, os.path.basename(link)))


def download_and_filter_urls(
        urls: list[str],
        api: GEDIAPI,
        beam_names: list[str],
        keep_obj: pd.DataFrame,
        shot_constraint: ShotConstraint,
        keep_every: int = 50,
        nproc: int = 1,
        out_dir: str = None,
        progess_bar: bool = True
):
    """
    Filter data from a collection of gedi granules in parallel, combining all shots meeting a constraint into
    a single dataframe/csv file. Files enter processing in lexigraphic order, but no guarantee on the output order of
    the data is possible unless nproc = 1. Additional columns added to the dataframe hold the granule id (e.g.
    "GEDI02_A_2020146010156_O08211_01_T02527_02_003_01_V002") and the beam name (e.g. "BEAM0101") of each shot.

    :param urls: A list of urls of h5 files containing the data. All should be the same product, e.g. L2A, or L1B,
                    but not a mix.
    :param api: A GEDIAPI object appropriate for accessing the urls.
    :param beamnames: A list of the beams of interest.
    :param keepobj: Contains columns for 'key', 'name', and 'index'. For instance, if keepobj is
                        {'key': ['lat_lowestmode', 'rh'], 'index': [None, 50], 'name': ['lat', 'rh50']}, then the
                        resulting dataframe will have the latitude of each shot stored in a column called 'lat', and
                        the 50th percentile rh metric stored in a column called 'rh50'.
    :param keepevery: create a representative sample using only one in every keep_every shots.
    :param shotconstraint: A ShotConstraint object to be applied to the resulting DataFrame.
    :param nproc: Number of parallel processes.
    :return: A dataframe with the filtered data from every granule
    :param progess_bar: If set to False, the progress bar is not printed. True by default.
    """
    urls = sorted(urls)
    args_list = [(link, api, beam_names, keep_obj, keep_every, shot_constraint, out_dir) for link in urls if not
    os.path.exists(os.path.join(out_dir, os.path.basename(link)))]
    if progess_bar:
        print(f"Filtering {nproc} files at a time; progress so far:")
    with futures.ThreadPoolExecutor(nproc) as executor:
        if progess_bar:
            progress_bar = tqdm(total=len(args_list))
        for arg in args_list:
            executor.submit(_process_granule, arg)
            if progess_bar:
                progress_bar.update(1)  # Update progress bar immediately upon submission
        if progess_bar:
            progress_bar.close()
