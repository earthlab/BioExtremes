import h5py
import numpy as np
import pandas as pd
import os
from multiprocessing import Pool
from tqdm import tqdm
import re

from gedi import L2A
from geometry import gch_intersects_region


# TODO: extra constraints should enforce spatial predicate to avoid code duplication
class GEDIShotConstraint:
    """
    Base class for a functor which filters a dataframe of GEDI shots. Automatically discards shots whose 'quality_flag'
    entries are not 1 and whose 'degrade_flag' entries are not 0. Subclasses enforce additional constraints.
    """

    def __call__(self, df: pd.DataFrame) -> None:
        # TODO: is it faster to drop flagged data first, then drop based on another constraint, or drop all at once?
        dropidx = df[(df['quality_flag'] == 0) | (df['degrade_flag'] != 0)].index
        df.drop(index=dropidx, inplace=True)
        self._extra_constraints(df)

    @classmethod
    def getkeys(cls):
        """Return names of objects expected in the dataframe. Subclasses should override _extra_names() method."""
        return ['quality_flag', 'degrade_flag'] + cls._extra_keys()

    @staticmethod
    def _extra_keys():
        return []

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        """May be overridden to drop additional shots in place."""
        pass

    def spatial_predicate(self, lon, lat) -> bool:
        """Should be overridden to enforce any spatial constraints."""
        return True


class LonLatBox(GEDIShotConstraint):
    """
    Call this functor on a dataframe with columns for 'longitude' and 'latitude'. Rows with coordinates
    outside a closed bounding box will be dropped. Note that longitude wraps at 180 = -180.
    """

    def __init__(self, minlon: float = -180, maxlon: float = 180, minlat: float = -90, maxlat: float = 90):
        self._minlon, self._minlat, self._maxlat = minlon, minlat, maxlat
        while maxlon <= minlon:
            maxlon += 360
        self._maxlont = (maxlon - minlon) % 360

    @staticmethod
    def _extra_keys():
        return ['lon_lowestmode', 'lat_lowestmode']

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        # use transformed longitudes in case bounding box crosses international date line
        lonst = (df['lon_lowestmode'] - self._minlon) % 360
        lats = df['lat_lowestmode']
        dropidx = df[(lonst > self._maxlont) | (lats < self._minlat) | (lats > self._maxlat)].index
        df.drop(index=dropidx, inplace=True)

    def spatial_predicate(self, lon, lat) -> bool:
        """Return whether a single point is inside the box."""
        lont = (lon - self._minlon) % 360
        return (lont <= self._maxlont) & (lat >= self._minlat) & (lat <= self._maxlat)


def filterl2abeam(
    gedil2a,
    beamname: str,
    keepobj: dict[str, str],
    keepevery: int = 1,
    constraindf: GEDIShotConstraint = GEDIShotConstraint(),
    csvdest: str = None
) -> pd.DataFrame:
    """
    Filter data from a single GEDI L2A beam during a quarter-orbit, so that only shots meeting a constraint are kept.
    Beam name is added to the dataframe.

    :param gedil2a: File-like object, or else absolute path to h5 file containing GEDI L2A data.
    :param beamname: name of a beam from which to filter data, e.g. 'BEAM0101'.
    :param keepobj: keys are objects under the beam to be stored; values are names to store them under. For example,
                    assigning colkeep['elev_lowestmode'] = 'elevation' will create a column titled 'elevation' in the
                    resulting dataframe whose contents come from gedil2a['[beamname]/elev_lowestmode'].
    :param keepevery: create a representative sample using only one in every keep_every shots.
    :param constraindf: A function whose input is a dataframe of GEDI shots with a column for each of
                        colnames. The function returns nothing but causes the dataframe to drop the
                        unwanted shots.
    :param csvdest: optional absolute path to a csv file in which to write data which passes the filter.
    :return: A dataframe containing the filtered data. Return nothing if an exception is caught.
    """
    gedil2a = h5py.File(gedil2a, 'r')
    df = {}
    keys = list(keepobj.keys()) + constraindf.getkeys()
    names = list(keepobj.values()) + constraindf.getkeys()
    for key, name in zip(keys, names):
        try:
            obj = beamname + '/' + key
            df[name] = gedil2a[obj][()][::keepevery]
        except KeyError:
            # TODO: what is happening? At least print the name of the file
            print(f'Download failed: could not receive data from {obj}')
            return
    df = pd.DataFrame(df)
    constraindf(df)
    df.drop(columns=[col for col in names if col not in keepobj.values()], inplace=True)
    # add beam name to df
    df['beam'] = [beamname for _ in range(df.shape[0])]
    if csvdest:
        df.to_csv(csvdest, mode='x')
    return df


def _filterl2afile(
        gedil2a,
        beamnames: list[str],
        keepobj: dict[str, str],
        keepevery: int,
        constraindf: GEDIShotConstraint
) -> pd.DataFrame:
    """
    First parameter is a file-like object with data to filter. Subsequent parameters are the beamnames, keepobj,
    keepevery, and constraindf arguments as used by downloadandfilterl2aurls(). Return a dataframe with the filtered
    data, or nothing if no data is extracted.
    """
    frames = []
    for beamname in beamnames:
        df = filterl2abeam(gedil2a, beamname, keepobj, keepevery=keepevery, constraindf=constraindf)
        if df is not None:
            frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _screenxmlpoly(xmlfile, constraint: GEDIShotConstraint) -> bool:
    """
    :param xmlfile: File-like object containing xml associated to granule.
    :param constraint: spatial_predicate method used to rule out granules not intersecting region of interest.
    :return: Where granule intersects region of interest.
    """
    xml = str(xmlfile.getvalue())
    lons = [plon[16:-17] for plon in re.findall("<PointLongitude>-?[0-9]\d*\.?\d+?</PointLongitude>", xml)]
    lats = [plon[15:-16] for plon in re.findall("<PointLatitude>-?[0-9]\d*\.?\d+?</PointLatitude>", xml)]
    points = np.vstack([lons, lats]).astype(float).T
    return gch_intersects_region(points, constraint.spatial_predicate)


def _filterl2aurl(args: tuple) -> pd.DataFrame:
    """
    Filter multiple beams from a GEDI granule. Inputs are taken in a single tuple for compatibility with
    multiprocessing.Pool.imap_unordered. Granule id is added to dataframe.

    :param args: Contains, in order, the remote url to the data, then the beamnames, keepobj, keepevery, and
                    constraindf arguments as used by downloadandfilterl2aurls().
    :return: Filtered data from all beams. Return nothing if no data is extracted.
    """
    l2a = L2A()
    link, beamnames, keepobj, keepevery, constraindf = args
    # screen associated xml file to see if data is from right spatial location
    xmlurl = link + '.xml'
    proceed = l2a.process_in_memory_file(
        xmlurl,
        _screenxmlpoly,
        constraindf
    )
    if proceed is False:    # may be None if an exception was caught
        return
    # now download and filter large h5 file
    df = l2a.process_in_memory_file(
        link,
        _filterl2afile,
        beamnames, keepobj, keepevery, constraindf
    )
    # add granule id to df
    istart = link.rindex('/') + 1
    iend = link.rindex('.')
    granule_id = link[istart:iend]
    df['granule_id'] = [granule_id for _ in range(df.shape[0])]
    return df


def downloadandfilterl2aurls(
    l2aurls: list[str],
    beamnames: list[str],
    keepobj: dict[str, str],
    keepevery: int = 1,
    constraindf: GEDIShotConstraint = GEDIShotConstraint(),
    nproc: int = 1,
    csvdest: str = None,
    progess_bar: bool = True
) -> pd.DataFrame:
    """
    TODO: replace constraindf with separate contraints to download and subset
    Filter data from a collection of GEDI L2A quarter-orbits in parallel, combining all shots meeting a constraint into
    a single dataframe/csv file. Files enter processing in lexigraphic order, but no guarantee on the output order of
    the data is possible unless nproc = 1. Additional columns added to the dataframe hold the granule id (e.g.
    "GEDI02_A_2020146010156_O08211_01_T02527_02_003_01_V002") and the beam name (e.g. "BEAM0101") of each shot.

    :param l2aurls: A list of urls of h5 files containing the data.
    :param beamnames: A list of the beams of interest.
    :param keepobj: Passed to filterl2abeam()
    :param keepevery: Passed to filterl2abeam()
    :param constraindf: Passed to filterl2abeam()
    :param nproc: Number of parallel processes.
    :param csvdest: Optional absolute path to a csv file where all data is written.
    :return: A dataframe with the filtered data from every quarter-orbit
    :param progess_bar: If set to False, progress bar is not printed. True by default.
    """
    if csvdest and os.path.exists(csvdest):
        raise ValueError(f'Can not overwrite prexisting file at {csvdest}')
    l2aurls = sorted(l2aurls)
    argslist = [(link, beamnames, keepobj, keepevery, constraindf) for link in l2aurls]
    if progess_bar:
        print(f"Filtering {nproc} files at a time; progress so far:")
    frames = []
    killed = False
    try:
        with Pool(nproc) as pool:
            sequence = map(_filterl2aurl, argslist)
            if progess_bar:
                sequence = tqdm(sequence, total=len(argslist))
            for df in sequence:
                if df is not None:
                    frames.append(df)
    except (KeyboardInterrupt, SystemExit):
        print(f'Filtering halted by user around {argslist[len(frames)][0]}')
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

