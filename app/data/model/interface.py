import abc
import enum
from dataclasses import dataclass
from typing import Any, Self

import numpy as np
from astropy import units as u


@dataclass
class MeasuredValue:
    value: Any
    unit: u.Unit


def is_nan(v: u.Quantity | None | float) -> bool:
    if isinstance(v, float):
        return np.isnan(v)

    if isinstance(v, u.Quantity):
        return np.isnan(v.value)

    return v is None


class RawCatalog(enum.Enum):
    """
    Enum that represents the catalogs in their original form. They are stored in two
    forms: one is the unaggregated collection of original data on layer 1 and the other is the
    aggregated data on layer 2.
    """

    ICRS = "icrs"
    DESIGNATION = "designation"
    ADDITIONAL_DESIGNATIONS = "additional_designations"
    REDSHIFT = "redshift"
    NATURE = "nature"
    PHOTOMETRY = "photometry"
    NOTE = "note"


RUNTIME_RAW_CATALOGS: frozenset[RawCatalog] = frozenset(
    {
        RawCatalog.ADDITIONAL_DESIGNATIONS,
    }
)


class CatalogObject(abc.ABC):
    """
    Represents an object stored in a particular catalog.
    """

    @abc.abstractmethod
    def catalog(self) -> RawCatalog:
        pass

    @classmethod
    @abc.abstractmethod
    def layer1_table(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def layer1_keys(cls) -> list[str]:
        pass

    @classmethod
    def layer1_primary_keys(cls) -> list[str]:
        return ["record_id"]

    @classmethod
    @abc.abstractmethod
    def from_layer1(cls, data: dict[str, Any]) -> Self:
        pass

    @classmethod
    @abc.abstractmethod
    def layer2_table(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def layer2_keys(cls) -> list[str]:
        pass

    @abc.abstractmethod
    def layer2_data(self) -> dict[str, Any]:
        pass

    @classmethod
    @abc.abstractmethod
    def from_layer2(cls, data: dict[str, Any]) -> Self:
        pass


def get_object[T](catalog_objects: list[CatalogObject], t: type[T]) -> T | None:
    for obj in catalog_objects:
        if isinstance(obj, t):
            return obj

    return None
