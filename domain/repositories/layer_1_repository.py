from abc import ABC, abstractmethod

from domain.model import Layer0Model


class Layer1Repository(ABC):
    """
    Provides access to layer 1 data
    """
    @abstractmethod
    def get_by_name(self, name: str) -> Layer0Model:
        pass

    @abstractmethod
    def get_inside_square(self, min_ra: float, max_ra: float, min_dec: float, max_dec: float):
        pass
