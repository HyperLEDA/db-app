from abc import ABC, abstractmethod
from typing import Optional

from app.domain.model import Layer1Model


class Layer1Repository(ABC):
    """
    Provides access to layer 1 data
    """

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Layer1Model]:
        pass

    @abstractmethod
    async def get_inside_square(
        self, min_ra: float, max_ra: float, min_dec: float, max_dec: float
    ) -> list[Layer1Model]:
        pass

    @abstractmethod
    async def save_update_instances(self, instances: list[Layer1Model]):
        pass
