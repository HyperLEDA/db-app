from dataclasses import dataclass
from abc import ABC


class Transformation01Stage(ABC):
    pass


@dataclass
class ParseCoordinates(Transformation01Stage):
    pass


@dataclass
class ParseValues(Transformation01Stage):
    pass


@dataclass
class CrossIdentification(Transformation01Stage):
    total: int
    progress: int
