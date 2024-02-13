from abc import ABC, abstractmethod

from domain.model import Layer0Model


class Layer0Repository(ABC):
    """
    Provides access to layer 0 data
    """
    @abstractmethod
    def save_update_instances(self, instances: list[Layer0Model]) -> bool:
        """
        Save or update given instances in local DB
        :param instances: Instances to update
        :return: Is operation successful
        """
        pass
