import abc
from typing import Any


class Filter(abc.ABC):
    @abc.abstractmethod
    def get_query(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> list[Any]:
        pass


class DesignationEqualsFilter(Filter):
    def __init__(self, designation: str):
        self._designation = designation

    def get_query(self):
        return "designation.design = %s"

    def get_params(self):
        return [self._designation]


class ICRSCoordinatesInRadiusFilter(Filter):
    def __init__(self, ra: float, dec: float, radius: float):
        self._ra = ra
        self._dec = dec
        self._radius = radius

    def get_query(self):
        return """
        ST_Distance(ST_MakePoint(%s, %s-180), ST_MakePoint(icrs.dec, icrs.ra-180)) < %s
        """

    def get_params(self):
        return [self._dec, self._ra, self._radius]
