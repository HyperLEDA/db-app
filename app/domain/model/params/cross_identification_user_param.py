from dataclasses import dataclass

from astropy.coordinates import Angle


@dataclass
class CrossIdentificationUserParam:
    r1: Angle | None
    r2: Angle | None
