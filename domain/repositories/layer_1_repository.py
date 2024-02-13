from abc import ABC, abstractmethod
from typing import Optional

from domain.model import Layer1Model


class Layer1Repository(ABC):
    """
    Provides access to layer 1 data
    """
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Layer1Model]:
        pass

    @abstractmethod
    def get_inside_square(self, min_ra: float, max_ra: float, min_dec: float, max_dec: float) -> list[Layer1Model]:
        pass

    @abstractmethod
    def save_update_instances(self, instances: list[Layer1Model]) -> bool:
        pass
