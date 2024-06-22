from abc import ABC, abstractmethod

from app.domain.model import Layer1Model
from app.domain.model.params.layer_1_query_param import Layer1QueryParam


class Layer1Repository(ABC):
    """
    Provides access to layer 1 data
    """

    @abstractmethod
    async def query_data(self, param: Layer1QueryParam) -> list[Layer1Model]:
        """
        Get all objects around given point
        :param param: Parameter, used to make specific query
        :return: all Layer1Model, that meet criteria in param
        """

    @abstractmethod
    async def save_update_instances(self, instances: list[Layer1Model]):
        """
        Create or update provided objects
        :param instances: Objects to be processed
        """
