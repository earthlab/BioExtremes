"""
This module contains tools for determining whether a GEDI granule has data within a region of interest.
"""

import numpy as np
import re
from abc import abstractmethod, ABC

from GEDI.api import GEDIAPI
from Spherical.arc import Polygon, SimplePiecewiseArc


class GranuleConstraint(ABC):
    """
    Functor used to apply granule-level constraints on GEDI data. Returns True for granules intersecting a region of
    interest.
    """

    @staticmethod
    def _polyfromxmlfile(xmlfile: str) -> Polygon:
        xml = str(xmlfile.getvalue())
        lons = [plon[16:-17] for plon in re.findall(r"<PointLongitude>-?\d*\.?\d+?</PointLongitude>", xml)]
        lats = [plon[15:-16] for plon in re.findall(r"<PointLatitude>-?\d*\.?\d+?</PointLatitude>", xml)]
        poly = np.array([lats, lons]).astype(float)
        poly = Polygon(np.flip(poly, axis=1), checksimple=False)
        return poly

    def getboundingpolygon(self, url) -> Polygon:
        """
        :param url: Link to a granule's associated xml file.
        :return: The bounding polygon of the granule listed by the xml file, as an ordered list of (lat, lon) points.
        """
        return self.api.process_in_memory_file(url, self._polyfromxmlfile)

    def __init__(self, api: GEDIAPI):
        """:param api: GEDIAPI object for data retrieval."""
        self.api = api

    @abstractmethod
    def _checkpoly(self, poly: Polygon) -> bool:
        """Apply the constraint to a granule's bounding polygon."""

    def __call__(self, url: str) -> tuple[bool, str]:
        """
        Determine whether the granule, indicated by the url of its associated xml file, passes the constraint.
        Return whether the granule passed, followed by the url itself.
        """
        poly = self.getboundingpolygon(url)
        return self._checkpoly(poly), url


class RegionGC(GranuleConstraint):
    """Accepts GEDI granules only whose bounding polygons interest a region defined by a closed SimplePiecewiseArc."""

    def __init__(self, region: SimplePiecewiseArc, api: GEDIAPI):
        """
        :param region: A SimplePiecewiseArc enclosing the region of interest
        :param api: Used to obtain data from server
        """
        if not region.isclosed():
            raise ValueError("Only a closed curve defines a region")
        self.region = region
        super().__init__(api)

    def _checkpoly(self, poly: Polygon) -> bool:
        if poly.intersections(self.region) is not None:
            return True
        if poly.contains(self.region(0)):
            return True
        if self.region.contains(poly(0)):
            return True
        return False


class CompositeGC(GranuleConstraint):
    """Accept based on an AND/OR of other GranuleConstraints."""

    def __init__(self, constraints: list[GranuleConstraint], disjunction: bool):
        """
        :param constraints: a list of GranuleConstraint objects.
        :param disjunction: boolean indicating whether to OR (True) or AND (False) the list of constraints.
        """
        self._gcs = constraints
        self._or = disjunction
        self.api = constraints[0].api

    def _checkpoly(self, poly: Polygon) -> bool:
        for gc in self._gcs:
            if gc._checkpoly(poly) == self._or:
                return self._or
        return not self._or
