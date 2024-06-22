from abc import ABC, abstractmethod

from app.domain.model.layer2 import Layer2Model
from app.domain.model.params.layer_2_query_param import Layer2QueryParam


class Layer2Repository(ABC):
    """
    Provides access to layer 2 data
    """

    @abstractmethod
    async def query_data(self, param: Layer2QueryParam) -> list[Layer2Model]:
        """
        Get all objects around given point
        :param param: Parameter, used to make specific query
        :return: all Layer2Model, that meet criteria in param
        """

    @abstractmethod
    async def save_update_instances(self, instances: list[Layer2Model]):
        """
        Create or update provided objects
        :param instances: Objects to be processed
        """
