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


def is_nan(v: MeasuredValue | None | float) -> bool:
    if isinstance(v, float):
        return np.isnan(v)

    return v is None or np.isnan(v.value)


class RawCatalog(enum.Enum):
    """
    Enum that represents the catalogs in their original form. They are stored in two
    forms: one is the unaggregated collection of original data on layer 1 and the other is the
    aggregated data on layer 2.
    """

    ICRS = "icrs"
    DESIGNATION = "designation"
    REDSHIFT = "redshift"


class CatalogObject(abc.ABC):
    """
    Represents an object stored in a particular catalog.
    """

    @classmethod
    @abc.abstractmethod
    def aggregate(cls, objects: list[Self]) -> Self:
        pass

    @abc.abstractmethod
    def catalog(self) -> RawCatalog:
        pass

    @abc.abstractmethod
    def layer0_data(self) -> dict[str, Any]:
        pass

    @classmethod
    @abc.abstractmethod
    def from_custom(cls, **kwargs) -> Self:
        pass

    @classmethod
    @abc.abstractmethod
    def layer1_table(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def layer1_keys(cls) -> list[str]:
        pass

    @abc.abstractmethod
    def layer1_data(self) -> dict[str, Any]:
        pass

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
