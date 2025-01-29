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


class CatalogObject(abc.ABC):
    """
    Represents an object stored in a particular catalog.
    """

    def __init__(self, pgc: int) -> None:
        self._pgc = pgc

    @classmethod
    @abc.abstractmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        pass

    @classmethod
    @abc.abstractmethod
    def layer2_keys(cls) -> list[str]:
        pass

    @abc.abstractmethod
    def pgc(self) -> int:
        pass

    @abc.abstractmethod
    def catalog(self) -> RawCatalog:
        pass

    @abc.abstractmethod
    def layer1_data(self) -> dict[str, Any]:
        pass

    @abc.abstractmethod
    def layer2_data(self) -> dict[str, Any]:
        pass


def get_catalog_object_type(catalog: RawCatalog) -> type[CatalogObject]:
    if catalog == RawCatalog.DESIGNATION:
        return DesignationCatalogObject
    if catalog == RawCatalog.ICRS:
        return ICRSCatalogObject

    raise ValueError(f"Unknown catalog: {catalog}")


def new_catalog_object(catalog: RawCatalog, pgc: int, **kwargs) -> CatalogObject:
    return get_catalog_object_type(catalog)(pgc, **kwargs)


def get_catalog_object(obj: entities.ObjectProcessingInfo) -> list[tuple[str, CatalogObject]]:
    objects = []

    if obj.pgc is None:
        return []

    if obj.data.primary_name is not None:
        objects.append((obj.object_id, DesignationCatalogObject(obj.pgc, obj.data.primary_name)))

    if obj.data.coordinates is not None:
        objects.append(
            (
                obj.object_id,
                ICRSCatalogObject(obj.pgc, obj.data.coordinates.ra.deg, 0.01, obj.data.coordinates.dec.deg, 0.02),
            )
        )

    return objects


@final
class DesignationCatalogObject(CatalogObject):
    def __init__(self, pgc: int, design: str, **kwargs) -> None:
        self.designation = design

        super().__init__(pgc)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, DesignationCatalogObject):
            return False

        return self.pgc() == value.pgc() and self.designation == value.designation

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

        return cls(objects[0].pgc(), max_name)

    def pgc(self) -> int:
        return self._pgc

    def catalog(self) -> RawCatalog:
        return RawCatalog.DESIGNATION

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["design"]

    def layer1_data(self) -> dict[str, Any]:
        return {
            "pgc": self.pgc(),
            "design": self.designation,
        }

    def layer2_data(self) -> dict[str, Any]:
        return {
            "design": self.designation,
        }


@final
class ICRSCatalogObject(CatalogObject):
    def __init__(self, pgc: int, ra: float, e_ra: float, dec: float, e_dec: float, **kwargs) -> None:
        self.ra = ra
        self.e_ra = e_ra
        self.dec = dec
        self.e_dec = e_dec

        super().__init__(pgc)

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ICRSCatalogObject):
            return False

        return (
            self.pgc() == value.pgc()
            and self.ra == value.ra
            and self.e_ra == value.e_ra
            and self.dec == value.dec
            and self.e_dec == value.e_dec
        )

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

        return cls(objects[0].pgc(), ra, e_ra, dec, e_dec)

    def pgc(self) -> int:
        return self._pgc

    def catalog(self) -> RawCatalog:
        return RawCatalog.ICRS

    @classmethod
    def layer2_keys(cls) -> list[str]:
        return ["ra", "e_ra", "dec", "e_dec"]

    def layer1_data(self) -> dict[str, Any]:
        return {
            "pgc": self.pgc(),
            "ra": self.ra,
            "e_ra": self.e_ra,
            "dec": self.dec,
            "e_dec": self.e_dec,
        }

    def layer2_data(self) -> dict[str, Any]:
        return {
            "ra": self.ra,
            "e_ra": self.e_ra,
            "dec": self.dec,
            "e_dec": self.e_dec,
        }
