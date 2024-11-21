"""
This module contains objects which enforce row-by-row contraints on DataFrames of gedi shots.
"""
from enums import GEDILevel

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

R_earth = 6378100   # equatorial radius in meters (astropy)


class ShotConstraint:
    """
    Base class for a functor which subsets a dataframe of gedi shots. Automatically discards shots whose 'quality_flag'
    entries are not 1 and whose 'degrade_flag' entries are not 0. Subclasses enforce additional constraints.
    """

    def __init__(self, file_level: GEDILevel):
        if file_level == GEDILevel.L2A:
            self._lon_col, self._lat_col = 'lon_lowestmode', 'lat_lowestmode'
            self._quality_equal = {'quality_flag': 0}
            self._quality_not_equal = {'degrade_flag': 0}
        elif file_level == GEDILevel.L2B:
            self._lon_col, self._lat_col = 'geolocation/longitude_bin0', 'geolocation/latitude_bin0'
            self._quality_equal = {'l2a_quality_flag': 0, 'l2b_quality_flag': 0}
            self._quality_not_equal = {'geolocation/degrade_flag': 0}

    def __call__(self, df: pd.DataFrame) -> None:
        # TODO: is it faster to drop flagged data first, then drop based on another constraint, or drop all at once?
        dropidx = df[
            np.logical_or.reduce(
                [(df[k] == v).values for k, v in self._quality_equal.items()] +
                [(df[k] != v).values for k, v in self._quality_not_equal.items()]
            )
        ].index
        df.drop(index=dropidx, inplace=True)
        self._extra_constraints(df)

    def get_keys(self):
        """
        Return names of the columns needed in the dataframe, e.g. 'quality_flag'.
        Subclasses override _extra_keys() method to ensure that all constrained columns are listed.
        """
        return list(self._quality_equal.keys()) + list(self._quality_not_equal.keys()) + self._extra_keys()

    @staticmethod
    def _extra_keys():
        return []

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        """Drop additional shots from df in-place based on other requirements."""
        pass

    def spatial_predicate(self, lon, lat) -> bool:
        """Should be overridden to enforce any spatial constraints."""
        return True


class SpatialShotConstraint(ShotConstraint):
    """Constrains latitude and longitude to a region of interest."""
    def __init__(self, file_level: GEDILevel):
        super().__init__(file_level)

    def _extra_keys(self):
        return [self._lon_col, self._lat_col]

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        raise NotImplementedError('SpatialShotConstraint is an abstract class, only subclasses should be constructed!')


# TODO: replace this with a regional constraint based on a SimplePiecewiseArc
class LatLonBox(SpatialShotConstraint):
    """
    Drop shots with coordinates outside a closed bounding box will be dropped. Note that longitude wraps at 180 = -180.
    """

    def __init__(self, file_level: GEDILevel, minlat: float = -90, maxlat: float = 90, minlon: float = -180,
                 maxlon: float = 180):
        super().__init__(file_level)
        self._minlon, self._minlat, self._maxlat = minlon, minlat, maxlat
        while maxlon <= minlon:
            maxlon += 360
        self._maxlont = (maxlon - minlon) % 360

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        # use transformed longitudes in case bounding box crosses international date line
        lonst = (df[self._lon_col] - self._minlon) % 360
        lats = df[self._lat_col]
        dropidx = df[(lonst > self._maxlont) | (lats < self._minlat) | (lats > self._maxlat)].index
        df.drop(index=dropidx, inplace=True)

    def spatial_predicate(self, lat, lon) -> bool:
        """Return whether a point is inside the box."""
        lont = (lon - self._minlon) % 360
        return (lont <= self._maxlont) & (lat >= self._minlat) & (lat <= self._maxlat)


class Buffer(SpatialShotConstraint):
    """Drop shots with coordinates farther that a fixed radius from a finite set of points."""

    def __init__(self, radius: float, points: np.ndarray, file_level: GEDILevel):
        """
        :param radius: should be in meters.
        :param points: should have two columns, latitudes then longitudes, in degrees.
        """
        super().__init__(file_level)
        self._r = radius / R_earth  # converted to Earth radii
        self._tree = BallTree(np.radians(points))

    def _extra_constraints(self, df: pd.DataFrame) -> None:
        lon, lat = df[self._lon_col], df[self._lat_col]
        query = np.vstack([lat, lon]).T
        query = np.radians(query)
        dist, _ = self._tree.query(query)
        dropidx = df[dist > self._r].index
        df.drop(index=dropidx, inplace=True)

