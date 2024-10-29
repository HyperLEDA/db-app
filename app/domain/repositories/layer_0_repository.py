from abc import ABC, abstractmethod

from app.domain.model import Layer0Model
from app.domain.model.params.layer_0_query_param import Layer0QueryParam


class Layer0Repository(ABC):
    """
    Provides access to layer 0 data
    """

    @abstractmethod
    def create_update_instances(self, instances: list[Layer0Model]):
        """
        Save or update given instances in local DB
        :param instances: Instances to update
        """

    @abstractmethod
    def create_instances(self, instances: list[Layer0Model]):
        """
        Used to create instances, fails on conflict
        :param instances:
        """

    @abstractmethod
    def fetch_data(self, param: Layer0QueryParam) -> list[Layer0Model]:
        """
        Fetches Layer0Model from DB
        :param param: Used to specify needed Layer0 instances
        :return: Fetched data models
        """
