from dataclasses import dataclass
from typing import Optional


@dataclass
class CrossIdentificationUserParam:
    r1: Optional[float]
    r2: Optional[float]
