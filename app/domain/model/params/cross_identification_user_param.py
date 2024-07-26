from dataclasses import dataclass
from typing import Optional

from astropy.coordinates import Angle


@dataclass
class CrossIdentificationUserParam:
    r1: Optional[Angle]
    r2: Optional[Angle]
