import abc
import enum
from typing import Any, Self, final

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

    @classmethod
    @abc.abstractmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        pass

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
    def __init__(self, pgc: int, object_id: str, design: str, **kwargs) -> None:
        self._pgc = pgc
        self._object_id = object_id
        self.designation = design

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        """
        Aggregate designation is selected as the most common designation among all objects.
        """
        name_counts = {}

        for obj in objects:
            name_counts[obj.designation] = name_counts.get(obj.designation, 0) + 1

        max_name = ""

        for name, count in name_counts.items():
            if count > name_counts.get(max_name, 0):
                max_name = name

        return cls(objects[0].pgc(), objects[0].object_id(), max_name)

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
    def __init__(self, pgc: int, object_id: str, ra: float, e_ra: float, dec: float, e_dec: float, **kwargs) -> None:
        self._pgc = pgc
        self._object_id = object_id
        self.ra = ra
        self.e_ra = e_ra
        self.dec = dec
        self.e_dec = e_dec

    @classmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        """
        Aggregate coordinates are computed as the mean of all coordinates.
        Errors are computed as the mean of all errors.
        """
        ras = [obj.ra for obj in objects]
        e_ras = [obj.e_ra for obj in objects]
        decs = [obj.dec for obj in objects]
        e_decs = [obj.e_dec for obj in objects]

        ra = sum(ras) / len(ras)
        e_ra = sum(e_ras) / len(e_ras)
        dec = sum(decs) / len(decs)
        e_dec = sum(e_decs) / len(e_decs)

        return cls(objects[0].pgc(), objects[0].object_id(), ra, e_ra, dec, e_dec)

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
