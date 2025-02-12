import datetime
from dataclasses import dataclass

from astropy.coordinates import ICRS, Angle


@dataclass
class Layer2Model:
    """
    Data model for layer 2. Represents processed (averaged) measurements
    Args:
        `pgc`: PGC. This object unique id
        `coordinates`: This object averaged coordinates in ICRS
        `names`: All known names for this object
        `common_name`: Common name for this object
        `err_ra`: RA error
        `err_dec`: DEC error
        `modified`: Last modification time
    """

    pgc: int
    coordinates: ICRS
    names: list[str]
    common_name: str | None
    err_ra: Angle
    err_dec: Angle
    modified: datetime.datetime
