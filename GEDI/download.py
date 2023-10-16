"""
This module provides a single public method, downloadandfilterurls(), which allows users to download data from a list
of GEDI granules, while specifying granule-level and shot-level constraints.
"""
import urllib.error
from typing import Callable
import h5py
import pandas as pd
import os
from multiprocessing import Pool
from tqdm import tqdm

from GEDI.api import L2AAPI
from GEDI.granuleconstraint import GranuleConstraint
from GEDI.shotconstraint import ShotConstraint


def _subsetbeam(
    granule,
    beam: str,
    keepobj: dict[str, str],
    keepevery: int = 1,
    constraindf: ShotConstraint = ShotConstraint()
) -> pd.DataFrame:
    """
    Subset the data from a single beam from a granule, so that only shots meeting a constraint are kept.
    Beam name is added to the dataframe.

    :param granule: File-like object, or else path to h5 file containing GEDI data.
    :param beam: name of a beam from which to filter data, e.g. 'BEAM0101'.
    :param keepobj: keys are objects under the beam to be stored; values are names to store them under. For example,
                    assigning colkeep['elev_lowestmode'] = 'elevation' will create a column titled 'elevation' in the
                    resulting dataframe whose contents come from granule['[beamname]/elev_lowestmode'].
    :param keepevery: create a representative sample using only one in every keep_every shots.
    :param constraindf: A function whose input is a dataframe of GEDI shots with a column for each of
                        colnames. The function returns nothing but causes the dataframe to drop the
                        unwanted shots.
    :return: A dataframe containing the filtered data. Return nothing if an exception is caught.
    """
    granule = h5py.File(granule, 'r')
    df = {}
    keys = list(keepobj.keys()) + constraindf.getkeys()
    names = list(keepobj.values()) + constraindf.getkeys()
    for key, name in zip(keys, names):
        obj = beam + '/' + key
        df[name] = granule[obj][()][::keepevery]
    df = pd.DataFrame(df)
    constraindf(df)
    df.drop(columns=[col for col in names if col not in keepobj.values()], inplace=True)
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
    keepevery, and constraindf arguments as used by downloadandfilterl2aurls(). Return a dataframe with the filtered
    data, or nothing if no data is extracted.
    """
    frames = []
    for beamname in beamnames:
        df = _subsetbeam(granule, beamname, keepobj, keepevery=keepevery, constraindf=constraindf)
        if df is not None:
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _processgranule(args: tuple) -> pd.DataFrame | str:
    """
    Filter multiple beams from a GEDI granule. Inputs are taken in a single tuple for compatibility with
    multiprocessing.Pool.imap_unordered. Granule id is added to dataframe.

    :param args: Contains, in order, the remote url to the data, then the beamnames, keepobj, keepevery,
                    granuleselector, and constraindf arguments as used by downloadandfilterl2aurls().
    :return: Filtered data from all beams. Returns the url if an URLError occurs or if the keys of keepobj are not
                present in the granule.
    """
    try:
        l2a = L2AAPI()  # TODO: choose which API based on link contents
        link, beamnames, keepobj, keepevery, granuleselector, constraindf = args
        # stop if this granule fails initial screening
        proceed = granuleselector(link)
        if proceed is False:    # may be None if an exception was caught
            return
        # download and filter large h5 file
        df = l2a.process_in_memory_file(
            link,
            _subsetgranule,
            beamnames, keepobj, keepevery, constraindf
        )
        # add granule id to df
        istart = link.rindex('/') + 1
        iend = link.rindex('.')
        granule_id = link[istart:iend]
        df['granule_id'] = [granule_id for _ in range(df.shape[0])]
        return df
    except (urllib.error.URLError, KeyError) as e:
        print(f"Error in filtering {link}: {e}")
        return link


def downloadandfilterurls(
    urls: list[str],
    beamnames: list[str],
    keepobj: dict[str, str],
    keepevery: int = 50,
    granuleselector: Callable[[str], bool] = GranuleConstraint(),
    constraindf: ShotConstraint = ShotConstraint(),
    nproc: int = 1,
    csvdest: str = None,
    progess_bar: bool = True
) -> pd.DataFrame:
    """
    Filter data from a collection of GEDIAPI L2AAPI quarter-orbits in parallel, combining all shots meeting a constraint into
    a single dataframe/csv file. Files enter processing in lexigraphic order, but no guarantee on the output order of
    the data is possible unless nproc = 1. Additional columns added to the dataframe hold the granule id (e.g.
    "GEDI02_A_2020146010156_O08211_01_T02527_02_003_01_V002") and the beam name (e.g. "BEAM0101") of each shot.

    :param urls: A list of urls of h5 files containing the data.
    :param beamnames: A list of the beams of interest.
    :param keepobj: keys are objects under the beam to be stored; values are names to store them under. For example,
                    assigning colkeep['elev_lowestmode'] = 'elevation' will create a column titled 'elevation' in the
                    resulting dataframe whose contents come from granule['[beamname]/elev_lowestmode'].
    :param keepevery: create a representative sample using only one in every keep_every shots.
    :param granuleselector: A function whose input is the url to a granule's h5 data file, and whose output (T/F)
                                determines whether that granule will be downloaded and subsetted. Default is always
                                True.
    :param constraindf: A ShotConstraint object to be applied to the resulting DataFrame.
    :param nproc: Number of parallel processes.
    :param csvdest: Optional absolute path to a csv file where all data is written.
    :return: A dataframe with the filtered data from every quarter-orbit
    :param progess_bar: If set to False, progress bar is not printed. True by default.
    """
    if csvdest and os.path.exists(csvdest):
        raise ValueError(f'Can not overwrite prexisting file at {csvdest}')
    urls = sorted(urls)
    argslist = [(link, beamnames, keepobj, keepevery, granuleselector, constraindf) for link in urls]
    if progess_bar:
        print(f"Filtering {nproc} files at a time; progress so far:")
    frames = []
    killed = False
    try:
        with Pool(nproc) as pool:
            sequence = map(_processgranule, argslist)
            if progess_bar:
                sequence = tqdm(sequence, total=len(argslist))
            for df in sequence:
                if type(df) == pd.DataFrame:    # df is a string if something went wrong
                    frames.append(df)
    except (KeyboardInterrupt, SystemExit):
        print(f'Filtering halted around {argslist[len(frames)][0]}')
        killed = True
    finally:
        if frames:
            df = pd.concat(frames, ignore_index=True)
            if csvdest:
                print(f'Saving filtered data to {csvdest}')
                df.to_csv(csvdest, mode='x')
        if killed:
            exit(130)
    return df

