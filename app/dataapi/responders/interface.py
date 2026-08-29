from abc import ABC, abstractmethod
from typing import Any

from app import catalogs


class ObjectResponder(ABC):
    """
    Interface for building a custom response for objects from Layer 2 of the database.
    """

    @abstractmethod
    def build_response_from_catalog(self, objects: list[catalogs.Layer2CatalogObject]) -> Any:
        pass
