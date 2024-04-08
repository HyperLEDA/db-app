from typing import Optional, Union

from domain.repositories.layer_1_repository import Layer1Repository
from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.usecases.exceptions import CrossIdentificationException


class CrossIdentifyUseCase:
    def __init__(self, repository_l1: Layer1Repository):
        self._repository_l1 = repository_l1
    """
    Finds an object by name or coordinates and return's it's id, or creates a new id, if it's a new object.
    If there is a collision, returns this collision description
    """

    async def invoke(self, param: CrossIdentificationParam) -> int | CrossIdentificationException:
        """
        :param param: Data, used to identify object
        :return: id for this object
        """
        # TODO implement
        pass

    async def make_new_id(self) -> int:
        return await self._repository_l1.make_new_id()
