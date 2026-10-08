import abc
import enum
from typing import Any, Self

from app.catalogs.layer1 import Catalog as Layer1Catalog


class Catalog(enum.Enum):
    ICRS = "icrs"
    DESIGNATION = "designation"
    ADDITIONAL_DESIGNATIONS = "additional_designations"
    REDSHIFT = "redshift"
    NATURE = "nature"
    PHOTOMETRY__TOTAL = "photometry_total"
    NOTE = "note"


class CatalogObject(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def catalog(cls) -> Catalog: ...

    @classmethod
    @abc.abstractmethod
    def table(cls) -> str: ...

    @classmethod
    @abc.abstractmethod
    def sources(cls) -> list[Layer1Catalog]: ...

    @classmethod
    def keys(cls) -> list[str]:
        raise NotImplementedError

    def to_row(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_row(cls, data: dict[str, Any]) -> Self:
        raise NotImplementedError
