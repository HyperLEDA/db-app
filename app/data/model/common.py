import abc
import enum
from typing import Any, final

from app import entities

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


def get_catalog_object_type(catalog: RawCatalog) -> type[CatalogObject]:
    if catalog == RawCatalog.DESIGNATION:
        return DesignationCatalogObject
    if catalog == RawCatalog.ICRS:
        return ICRSCatalogObject

    raise ValueError(f"Unknown catalog: {catalog}")


def get_catalog_object(obj: entities.ObjectProcessingInfo) -> list[CatalogObject]:
    return [
        DesignationCatalogObject(obj.pgc, obj.object_id, obj.data.primary_name),
        ICRSCatalogObject(
            obj.pgc, obj.object_id, obj.data.coordinates.ra.deg, obj.data.coordinates.dec.deg, 0.01, 0.02
        ),
    ]


@final
class DesignationCatalogObject(CatalogObject):
    def __init__(self, pgc: int, object_id: str, design: str) -> None:
        self._pgc = pgc
        self._object_id = object_id
        self.designation = design

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
