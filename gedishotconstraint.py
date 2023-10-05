"""
This module contains objects which enforce row-by-row contraints on DataFrames of GEDI shots.
"""

import pandas as pd


class GEDIShotConstraint:
    """
    Base class for a functor which subsets a dataframe of GEDI shots. Automatically discards shots whose 'quality_flag'
    entries are not 1 and whose 'degrade_flag' entries are not 0. Subclasses enforce additional constraints.
    """

    def __call__(self, df: pd.DataFrame) -> None:
        # TODO: is it faster to drop flagged data first, then drop based on another constraint, or drop all at once?
        dropidx = df[(df['quality_flag'] == 0) | (df['degrade_flag'] != 0)].index
        df.drop(index=dropidx, inplace=True)
        self._extra_constraints(df)

    @classmethod
    def getkeys(cls):
        """
        Return names of the columns needed in the dataframe, e.g. 'quality_flag'.
        Subclasses override _extra_keys() method to ensure that all constrained columns are listed.
        """
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
        """Return whether a point is inside the box."""
        lont = (lon - self._minlon) % 360
        return (lont <= self._maxlont) & (lat >= self._minlat) & (lat <= self._maxlat)
