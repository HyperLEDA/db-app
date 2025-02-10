import abc
import enum
from typing import Any, Self


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

    @classmethod
    @abc.abstractmethod
    def layer1_table(cls) -> str:
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
