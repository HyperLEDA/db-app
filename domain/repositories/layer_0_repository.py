from abc import ABC, abstractmethod

from domain.model import Layer0Model


class Layer0Repository(ABC):
    """
    Provides access to layer 0 data
    """
    @abstractmethod
    async def create_update_instances(self, instances: list[Layer0Model]):
        """
        Save or update given instances in local DB
        :param instances: Instances to update
        """
        pass

    @abstractmethod
    async def create_instances(self, instances: list[Layer0Model]):
        """
        Used to create instances, fails on conflict
        :param instances:
        """
        pass
