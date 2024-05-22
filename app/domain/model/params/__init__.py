from abc import ABC, abstractmethod
from dataclasses import dataclass

from astropy.coordinates import ICRS, Angle

from app.domain.model.params.cross_identification_param import CrossIdentificationParam

__all__ = ["CrossIdentificationParam", "TmpDataRepositoryQueryParam"]


class TmpDataRepositoryQueryParam(ABC):
    @abstractmethod
    def table_name(self):
        pass


@dataclass
class TmpCoordinateTableQueryParam(TmpDataRepositoryQueryParam):
    """
    Parameter to query coordinates in some circle on the sky
    Args:
        `name`: Name of temporary table
        `center`: Center of query circle
        `r`: Radius of query circle
    """
    name: str
    center: ICRS
    r: Angle

    def table_name(self):
        return self.name
