import abc
import enum
from typing import Any, final

pgc = int


class RawCatalog(enum.Enum):
    """
    Enum that represents the catalogs in their original form. They are stored in two
    forms: one is the unaggregated collection of original data on layer 1 and the other is the
    aggregated data on layer 2.
    """

    ICRS = "icrs"
    DESIGNATION = "designation"


class Catalog(enum.Enum):
    """
    Enum that respesents catalogs that are physical quantities. They are obtained from
    raw catalogs on layer 2 by computing some physical quantity from the raw data.
    """


class CatalogObject(abc.ABC):
    """
    Represents an object stored in a particular catalog.
    """

    @abc.abstractmethod
    def pgc(self) -> int:
        pass

    @abc.abstractmethod
    def object_id(self) -> str:
        pass

    @abc.abstractmethod
    def catalog(self) -> RawCatalog:
        pass

    @abc.abstractmethod
    def data(self) -> dict[str, Any]:
        pass


@final
class DesignationCatalogObject(CatalogObject):
    def __init__(self, pgc: int, object_id: str, designation: str) -> None:
        self._pgc = pgc
        self._object_id = object_id
        self.designation = designation

    def pgc(self) -> int:
        return self._pgc

    def object_id(self) -> str:
        return self._object_id

    def catalog(self) -> RawCatalog:
        return RawCatalog.DESIGNATION

    def data(self) -> dict[str, Any]:
        return {
            "pgc": self.pgc(),
            "object_id": self.object_id(),
            "design": self.designation,
        }


@final
class ICRSCatalogObject(CatalogObject):
    def __init__(self, pgc: int, object_id: str, ra: float, e_ra: float, dec: float, e_dec: float) -> None:
        self._pgc = pgc
        self._object_id = object_id
        self.ra = ra
        self.e_ra = e_ra
        self.dec = dec
        self.e_dec = e_dec

    def pgc(self) -> int:
        return self._pgc

    def object_id(self) -> str:
        return self._object_id

    def catalog(self) -> RawCatalog:
        return RawCatalog.ICRS

    def data(self) -> dict[str, Any]:
        return {
            "pgc": self.pgc(),
            "object_id": self.object_id(),
            "ra": self.ra,
            "e_ra": self.e_ra,
            "dec": self.dec,
            "e_dec": self.e_dec,
        }
