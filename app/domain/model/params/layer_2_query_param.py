from abc import ABC
from dataclasses import dataclass

from astropy.coordinates import ICRS, Angle


class Layer2QueryParam(ABC):
    pass


@dataclass
class Layer2QueryByNames(Layer2QueryParam):
    names: list[str]


@dataclass
class Layer2QueryInCircle(Layer2QueryParam):
    center: ICRS
    r: Angle
