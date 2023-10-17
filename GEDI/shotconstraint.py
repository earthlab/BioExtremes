"""
This module contains objects which enforce row-by-row contraints on DataFrames of GEDI shots.
"""
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

R_earth = 6378100   # equatorial radius in meters (astropy)


class ShotConstraint:
    """
    Base class for a functor which subsets a dataframe of GEDI shots. Automatically discards shots whose 'quality_flag'
    entries are not 1 and whose 'degrade_flag' entries are not 0. Subclasses enforce additional constraints.
    """

    def __call__(self, df: pd.DataFrame) -> None:
        # TODO: is it faster to drop flagged data first, then drop based on another constraint, or drop all at once?
        dropidx = df[(df['quality_flag'] == 0) | (df['degrade_flag'] != 0)].index
        df.drop(index=dropidx, inplace=True)
        if len(df.index):   # df has rows
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


class SpatialShotConstraint(ShotConstraint):
    """Constrains latitude and longitude to a region of interest."""

    @staticmethod
    def _extra_keys():
        return ['lon_lowestmode', 'lat_lowestmode']

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        raise NotImplementedError('SpatialShotConstraint is an abstract class, only subclasses should be constructed!')


class LatLonBox(SpatialShotConstraint):
    """
    Drop shots with coordinates outside a closed bounding box will be dropped. Note that longitude wraps at 180 = -180.
    """

    def __init__(self, minlat: float = -90, maxlat: float = 90, minlon: float = -180, maxlon: float = 180):
        self._minlon, self._minlat, self._maxlat = minlon, minlat, maxlat
        while maxlon <= minlon:
            maxlon += 360
        self._maxlont = (maxlon - minlon) % 360

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        # use transformed longitudes in case bounding box crosses international date line
        lonst = (df['lon_lowestmode'] - self._minlon) % 360
        lats = df['lat_lowestmode']
        dropidx = df[(lonst > self._maxlont) | (lats < self._minlat) | (lats > self._maxlat)].index
        df.drop(index=dropidx, inplace=True)

    def spatial_predicate(self, lat, lon) -> bool:
        """Return whether a point is inside the box."""
        lont = (lon - self._minlon) % 360
        return (lont <= self._maxlont) & (lat >= self._minlat) & (lat <= self._maxlat)


class Buffer(SpatialShotConstraint):
    """Drop shots with coordinates farther that a fixed radius from a discrete set of points."""

    def __init__(self, radius: float, points: np.ndarray):
        """
        :param radius: should be in meters.
        :param points: should have two columns, latitudes then longitudes, in degrees.
        """
        self._r = radius / R_earth  # converted to Earth radii
        self._tree = BallTree(np.radians(points))

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        lon, lat = df['lon_lowestmode'], df['lat_lowestmode']
        query = np.vstack([lat, lon]).T
        query = np.radians(query)
        dist, _ = self._tree.query(query)
        dropidx = df[dist > self._r].index
        df.drop(index=dropidx, inplace=True)

