from domain.model import Layer0Model
from domain.model.params.cross_identification_param import CrossIdentificationParam


class CrossIdentificationException(BaseException):
    """
    Describes collisions from cross identification use case
    """
    def __init__(self, target_param: CrossIdentificationParam, collisions: list[Layer0Model]):
        """
        :param target_param: The configuration, that caused collision
        :param collisions: The collided objects from DB
        """
        self.target_param: CrossIdentificationParam = target_param
        self.collisions: list[Layer0Model] = collisions
