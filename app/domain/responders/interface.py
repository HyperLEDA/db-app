from abc import ABC, abstractmethod
from typing import Any

from app.data import model


class ObjectResponder(ABC):
    """
    Interface for building a custom response for objects from Layer 2 of the database.
    """

    @abstractmethod
    def build_response(self, objects: list[model.Layer2Object]) -> Any:
        pass
