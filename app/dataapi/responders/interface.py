from abc import ABC, abstractmethod
from typing import Any

from app.catalogs import layer2


class ObjectResponder(ABC):
    """
    Interface for building a custom response for objects from Layer 2 of the database.
    """

    @abstractmethod
    def build_response_from_catalog(self, objects: list[layer2.Layer2Object]) -> Any:
        pass
