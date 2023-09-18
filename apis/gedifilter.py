import h5py
import pandas as pd
import os

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
    csvdest: str = None,
    keepevery: int = 1,
    constraindf=GEDIShotConstraint()
) -> pd.DataFrame:
    """
    Filter data from a single GEDI L2A beam during a quarter-orbit, so that only shots meeting a constraint are kept.

    :param gedil2a: h5py.File object, or else absolute path to h5 file containing GEDI L2A data.
    :param beamname: name of a beam from which to filter data, e.g. 'BEAM0101'.
    :param keepobj: keys are objects under the beam to be stored; values are names to store them under. For example,
                    assigning colkeep['elev_lowestmode'] = 'elevation' will create a column titled 'elevation' in the
                    resulting dataframe whose contents come from gedil2a['[beamname]/elev_lowestmode'].
    :param csvdest: optional absolute path to a csv file in which to write data which passes the filter.
    :param keepevery: create a representative sample using only one in every keep_every shots.
    :param constraindf: A function whose input is a dataframe of GEDI shots with a column for each of
                        colnames. The function returns nothing but causes the dataframe to drop the
                        unwanted shots.
    :return: A dataframe containing the filtered data.
    """
    if type(gedil2a) == str:
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


def downloadandfilterl2a(
    l2aurls,
    beamnames: list[str],
    keepobj: dict[str, str],
    wdir: str,
    csvdest: str = None,
    keepevery: int = 1,
    constraindf=GEDIShotConstraint(),
) -> pd.DataFrame:
    """
    Filter data from a collection of GEDI L2A quarter-orbits, combining all shots meeting a constraint into a single
    dataframe/csv file.

    :param l2aurls: An iterable collection of urls of h5 files containing the data.
    :param beamnames: A list of the beams of interest, e.g. ['BEAM0101', 'BEAM0110'].
    :param keepobj: Passed to filterl2abeam()
    :param wdir: Absolute path to working directory for downloading quarter orbits.
    TODO: should use memory files rather than storing/deleting on disk
    :param csvdest: Absolute path to file where all data is stored.
    :param keepevery: Passed to filterl2abeam()
    :param constraindf: Passed to filterl2abeam()
    :return: A dataframe with the filtered data from every quarter-orbit
    """
    l2a = L2A()
    df = pd.DataFrame({})
    for link in l2aurls:
        print('Processing %s ...' % link)
        l2a._download((link, wdir + 'temp.h5'))
        for beamname in beamnames:
            newdata = filterl2abeam(wdir + 'temp.h5', beamname, keepobj, keepevery=keepevery, constraindf=constraindf)
            df = pd.concat([df, newdata], ignore_index=True)
        os.remove(wdir + 'temp.h5')
    if csvdest:
        df.to_csv(csvdest)
    return df
