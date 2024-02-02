"""
This module provides a single public method, downloadandfilterurls(), which allows users to download data from a list
of GEDI granules, while specifying granule-level and shot-level constraints.
"""

from typing import Callable
import h5py
import pandas as pd
import os
from concurrent import futures
from tqdm import tqdm

from GEDI.api import GEDIAPI
from GEDI.shotconstraint import ShotConstraint


def _subsetbeam(
        granule,
        beam: str,
        keepobj: pd.DataFrame,
        keepevery: int,
        constraindf: ShotConstraint,
) -> pd.DataFrame:
    """
    Subset the data from a single beam from a granule, so that only shots meeting a constraint are kept.
    Beam name is added to the dataframe.
    """
    granule = h5py.File(granule, 'r')
    df = {}
    keys = list(keepobj['key']) + constraindf.getkeys()
    names = list(keepobj['name']) + constraindf.getkeys()
    indices = list(keepobj['index']) + [None for _ in constraindf.getkeys()]
    for key, name, idx in zip(keys, names, indices):
        try:
            obj = beam + '/' + key
            try:
                idx = int(idx)
                df[name] = granule[obj][()][::keepevery, int(idx)]
            except (ValueError, TypeError):  # idx cannot be cast to int
                df[name] = granule[obj][()][::keepevery]
        except KeyError:
            # TODO: what is happening? At least print the name of the file
            print(f'Download failed: could not receive data from {obj}')
            return
    df = pd.DataFrame(df)
    constraindf(df)
    df.drop(columns=[col for col in names if not (col == keepobj['name']).any()], inplace=True)
    # add beam name to df
    df['beam'] = [beam for _ in range(df.shape[0])]
    return df


def _subsetgranule(
        granule,
        beamnames: list[str],
        keepobj: dict[str, str],
        keepevery: int,
        constraindf: ShotConstraint
) -> pd.DataFrame:
    """
    First parameter is a file-like object with data to filter. Subsequent parameters are the beamnames, keepobj,
    keepevery, and shotconstraint arguments as used by downloadandfilterl2aurls(). Return a dataframe with the filtered
    data, or nothing if no data is extracted.
    """
    frames = []
    for beamname in beamnames:
        df = _subsetbeam(granule, beamname, keepobj, keepevery=keepevery, constraindf=constraindf)
        if df is not None:
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _processgranule(args: tuple) -> pd.DataFrame:
    """
    Filter multiple beams from a GEDI granule. Inputs are taken in a single tuple for compatibility with
    multiprocessing.Pool.imap_unordered. Granule id is added to dataframe.

    :param args: Contains, in order, the remote url to the data, an appropriate GEDIAPI object to access that link,
                    then the beamnames, keepobj, keepevery, and shotconstraint arguments as used by
                    downloadandfilterl2aurls().
    :return: Filtered data from all beams. Return nothing if no data is extracted.
    """
    link, api, beamnames, keepobj, keepevery, constraindf, outdir = args
    # download and filter large h5 file
    df = api.process_in_memory_file(
        link,
        _subsetgranule,
        beamnames, keepobj, keepevery, constraindf
    )
    # add granule id to df
    istart = link.rindex('/') + 1
    iend = link.rindex('.')
    granule_id = link[istart:iend]
    df['granule_id'] = [granule_id for _ in range(df.shape[0])]
    print(f'Writing {link}')
    df.tocsv(os.path.join(outdir, os.path.basename(link)))


def downloadandfilterurls(
        urls: list[str],
        api: GEDIAPI,
        beamnames: list[str],
        keepobj: pd.DataFrame,
        keepevery: int = 50,
        shotconstraint: ShotConstraint = ShotConstraint(),
        nproc: int = 1,
        outdir: str = None,
        progess_bar: bool = True
) -> pd.DataFrame:
    """
    Filter data from a collection of GEDI granules in parallel, combining all shots meeting a constraint into
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
    :param csvdest: Optional absolute path to a csv file where all data is written.
    :return: A dataframe with the filtered data from every granule
    :param progess_bar: If set to False, the progress bar is not printed. True by default.
    """
    urls = sorted(urls)
    argslist = [(link, api, beamnames, keepobj, keepevery, shotconstraint, outdir) for link in urls if not
    os.path.exists(os.path.join(outdir, os.path.basename(link)))]
    if progess_bar:
        print(f"Filtering {nproc} files at a time; progress so far:")
    with futures.ThreadPoolExecutor(nproc) as executor:
        if progess_bar:
            progress_bar = tqdm(total=len(argslist))
        for arg in argslist:
            executor.submit(_processgranule, arg)
            if progess_bar:
                progress_bar.update(1)  # Update progress bar immediately upon submission
        if progess_bar:
            progress_bar.close()
