"""
This module contains tools for determining whether a GEDI granule has data within a region of interest.
"""

import numpy as np
import re

from gediapi import L2AAPI
from geometry import gch_intersects_region  # TODO: stop using this; it's hacky and slow


class GEDIGranuleConstraint:
    """
    Functor used to apply granule-level constraints on GEDI data. Returns True for granules intersecting a region of
    interest.
    """

    getxmlurl = lambda h5url: h5url + '.xml'

    @staticmethod
    def _polyfromxmlfile(xmlfile):
        xml = str(xmlfile.getvalue())
        lons = [plon[16:-17] for plon in re.findall("<PointLongitude>-?[0-9]\d*\.?\d+?</PointLongitude>", xml)]
        lats = [plon[15:-16] for plon in re.findall("<PointLatitude>-?[0-9]\d*\.?\d+?</PointLatitude>", xml)]
        points = np.vstack([lats, lons]).astype(float).T
        return points

    @classmethod
    def getboundingpolygon(cls, url) -> np.ndarray:
        """
        :param url: Link to a granule's associated h5 file.
        :return: The bounding polygon of the granule listed by the xml file, as an ordered list of (lat, lon) vertices.
        """
        l2a = L2AAPI()  # TODO: choose which API based on link contents
        xmlurl = cls.getxmlurl(url)
        return l2a.process_in_memory_file(xmlurl, cls._polyfromxmlfile)

    def __init__(self, spatial_predicate=lambda *args, **kwargs: True):
        self._spacepred = spatial_predicate

    def __call__(self, url):
        points = self.getboundingpolygon(url)
        return gch_intersects_region(points, self._spacepred)

