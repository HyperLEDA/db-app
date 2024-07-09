from dataclasses import dataclass
from typing import Optional

from astropy.coordinates import ICRS


@dataclass
class CrossIdentificationParam:
    """
    :param names: All names, provided by source
    :param primary_name: The name, that is provided as primary by author of transaction
    :param coordinates: Sky coordinates of the object
    """

    names: Optional[list[str]]
    primary_name: Optional[str]
    coordinates: Optional[ICRS]
