from astropy.coordinates import SkyCoord
from pandas import DataFrame, Series
from typing import Iterable, Any

from .coordinate_descr import CoordinateDescr


class ICRSDescrStr(CoordinateDescr):
    """
    Parses 'icrs' string representation.  Containing icrs data may be one column, with data
    like '00h42m30s +41d12m00s', or two columns for 'ra' and 'dec' respectively.
    """

    def _parse_row(self, data: Iterable[Any]) -> SkyCoord:
        return SkyCoord(*data, frame='icrs')
