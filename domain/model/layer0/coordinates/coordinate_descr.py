from abc import ABC, abstractmethod
from astropy.coordinates import SkyCoord
from pandas import DataFrame


class CoordinateDescr(ABC):
    """
    Class, responsible to parse coordinates of certain types
    """
    @abstractmethod
    def parse_coordinates(self, coordinates: DataFrame) -> list[SkyCoord]:
        pass
