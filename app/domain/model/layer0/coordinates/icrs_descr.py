from typing import Any, Iterable

import astropy.units as u
from astropy.coordinates import SkyCoord

from app.domain.model.layer0.coordinates.coordinate_descr import CoordinateDescr

ICRS_DESCR_ID = "icrs"


class ICRSDescrStr(CoordinateDescr):
    """
    Parses 'icrs' string representation.  Containing icrs data may be one column, with data
    like '00h42m30s +41d12m00s', or two columns for 'ra' and 'dec' respectively.
    """

    def description_id(self):
        return ICRS_DESCR_ID

    def _parse_row(self, data: Iterable[Any]) -> SkyCoord:
        return SkyCoord(*data, frame="icrs", unit=(u.hourangle, u.deg))
