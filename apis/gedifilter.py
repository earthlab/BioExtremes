import h5py
import pandas as pd
from io import BytesIO
import os
from multiprocessing import Pool

from gedi import L2A


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

    def _extra_constraints(self, df: pd.DataFrame):
        """May be overridden to drop additional shots in place."""
        pass


class LonLatBox(GEDIShotConstraint):
    """
    Call this functor on a dataframe with columns for 'longitude' and 'latitude'. Rows with coordinates
    outside a bounding box will be dropped. Note that longitude wraps at 180 = -180.
    """

    def __init__(self, minlon: float = -180, maxlon: float = 180, minlat: float = -90, maxlat: float = 90):
        self._minlon, self._maxlon, self._minlat, self._maxlat = minlon, maxlon, minlat, maxlat

    # overridden from parent
    @staticmethod
    def _extra_keys():
        return ['lon_lowestmode', 'lat_lowestmode']

    # override parent method
    def _extra_constraints(self, df: pd.DataFrame):
        # use transformed longitudes in case bounding box crosses international date line
        lonst = (df['lon_lowestmode'] - self._minlon) % 360
        maxlon = (self._maxlon - self._minlon) % 360
        lats = df['lat_lowestmode']
        dropidx = df[(lonst > maxlon) | (lats < self._minlat) | (lats > self._maxlat)].index
        df.drop(index=dropidx, inplace=True)


def filterl2abeam(
    gedil2a,
    beamname: str,
    keepobj: dict[str, str],
    keepevery: int = 1,
    constraindf=GEDIShotConstraint(),
    csvdest: str = None
) -> pd.DataFrame:
    """
    Filter data from a single GEDI L2A beam during a quarter-orbit, so that only shots meeting a constraint are kept.

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
    :return: A dataframe containing the filtered data.
    """
    gedil2a = h5py.File(gedil2a, 'r')
    df = {}
    keys = list(keepobj.keys()) + constraindf.getkeys()
    names = list(keepobj.values()) + constraindf.getkeys()
    for key, name in zip(keys, names):
        df[name] = gedil2a[beamname + '/' + key][()][::keepevery]
    df = pd.DataFrame(df)
    constraindf(df)
    df.drop(columns=[col for col in names if col not in keepobj.values()])
    if csvdest:
        df.to_csv(csvdest, mode='x')
    return df


def _filterl2aurl(args: tuple) -> pd.DataFrame:
    """
    Filter multiple beams from a GEDI quarter-orbit. Inputs are taken in a single tuple for compatibility with
    multiprocessing.Pool.imap_unordered.

    :param args: Contains, in order, the remote url of the data file at usgs.gov, a list of L2A beam names, then the
    keepobj, keepevery, and constraindf arguments as used by filterl2abeam().
    :return: Filtered data from all beams.
    """
    frames = []
    link, beamnames, keepobj, keepevery, constraindf = args

    print('Processing %s ...' % link)
    response = L2A().request_raw_data(link)
    response.begin()
    with BytesIO() as gedil2a:
        while True:
            chunk = response.read()
            if chunk:
                gedil2a.write(chunk)
            else:
                break
        for beamname in beamnames:
            df = filterl2abeam(gedil2a, beamname, keepobj, keepevery=keepevery, constraindf=constraindf)
            frames.append(df)
    print(f'Processed {link}')

    return pd.concat(frames, ignore_index=True)


def downloadandfilterl2a(
    l2aurls,
    beamnames: list[str],
    keepobj: dict[str, str],
    keepevery: int = 1,
    constraindf=GEDIShotConstraint(),
    nproc: int = 1,
    csvdest: str = None
) -> pd.DataFrame:
    """
    Filter data from a collection of GEDI L2A quarter-orbits, combining all shots meeting a constraint into a single
    dataframe/csv file.

    :param l2aurls: An iterable collection of urls of h5 files containing the data.
    :param beamnames: A list of the beams of interest, e.g. ['BEAM0101', 'BEAM0110'].
    :param keepobj: Passed to filterl2abeam()
    :param keepevery: Passed to filterl2abeam()
    :param constraindf: Passed to filterl2abeam()
    :param nproc: Number of processes. Parallelization removes any guarantee on the order in which shots appear in the
                    resulting dataframe.
    :param csvdest: Optional absolute path to a csv file where all data is written.
    :return: A dataframe with the filtered data from every quarter-orbit
    """
    if csvdest and os.path.exists(csvdest):
        raise ValueError(f'Can not overwrite prexisting file at {csvdest}')
    argslist = [(link, beamnames, keepobj, keepevery, constraindf) for link in l2aurls]
    print(f"Parallelizing filtering across {nproc} processes...")
    with Pool(nproc) as pool:
        frames = [df for df in pool.imap_unordered(_filterl2aurl, argslist)]
    df = pd.concat(frames, ignore_index=True)
    if csvdest:
        df.to_csv(csvdest, mode='x')
    return df

