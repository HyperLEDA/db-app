from dataclasses import dataclass
from typing import Optional

from astropy.coordinates import SkyCoord


@dataclass
class CrossIdentificationParam:
    """
    :param name: Well known name of the object
    :param coordinates: Sky coordinates of the object
    """

    name: Optional[str]
    coordinates: Optional[SkyCoord]
