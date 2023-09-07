import h5py
import pandas as pd


class GEDIShotConstraint:
    """
    Base class for a functor which filters a dataframe of GEDI shots. Automatically discards shots whose 'Quality Flag'
    entries are not 1. Subclasses enforce additional constraints.
    """

    def __call__(self, df: pd.DataFrame) -> None:
        dropidx = df[df['quality_flag'] == 0].index
        df.drop(index=dropidx, inplace=True)
        self._extra_constraints(df)

    def _extra_constraints(self, df: pd.DataFrame):
        """May be overridden to drop additional shots."""
        pass


class LonLatBox(GEDIShotConstraint):
    """
    Call this functor on a dataframe with columns for 'longitude' and 'latitude'. Rows with coordinates
    outside a bounding box will be dropped. Note that longitude wraps at 180 = -180.
    """

    def __init__(self, minlon: float = -180, maxlon: float = 180, minlat: float = -90, maxlat: float = 90):
        self._minlon, self._maxlon, self._minlat, self._maxlat = minlon, maxlon, minlat, maxlat

    # override parent method
    def _extra_constraints(self, df: pd.DataFrame):
        # transform longitudes in case box crosses date line
        lons = (df['longitude'] - self._minlon) % 360
        maxlon = (self._maxlon - self._minlon) % 360
        dropidx = df[(lons > maxlon) | (df['latitude'] < self._minlat) | (df['latitude'] > self._maxlat)].index
        df.drop(index=dropidx, inplace=True)


def filterl2a(
        h5file: str,
        colkeys: list[str],
        colnames: list[str],
        csvdest: str = None,
        keep_every: int = 1,
        constraindf=GEDIShotConstraint()) -> pd.DataFrame:
    """
    :param h5file: absolute path to an h5 file containing GEDI L2A data.
    :param colkeys: keys of interest from h5 dataset, e.g. 'BEAM0101/elev_lowestmode'
    :param colnames: desired name of column corresponding to each key in output file, e.g. 'elevation'
    :param csvdest: optional absolute path to a csv file in which to write data which passes the filter.
    :param keep_every: create a representative sample using only one in every keep_every shots.
    :param constraindf: A function whose input is a dataframe of GEDI shots with a column for each of
                        colnames. The function returns nothing but causes the dataframe to drop the
                        unwanted shots.
    :return: A dataframe containing the filtered data.
    """
    gedil2a = h5py.File(h5file, 'r')
    df = {}
    for key, name in zip(colkeys, colnames):
        df[name] = gedil2a[key][()][::keep_every]
    df = pd.DataFrame(df)
    constraindf(df)
    if csvdest:
        df.to_csv(csvdest)
    return df

