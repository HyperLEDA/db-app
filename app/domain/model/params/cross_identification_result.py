from __future__ import annotations

from app.domain.model.layer2 import Layer2Model
from app.domain.model.params.cross_identification_param import CrossIdentificationParam


class CrossIdentifyResult:
    def __init__(self, result: Layer2Model | None, fail: CrossIdentificationException | None):
        """
        :param result: None if new object, Layer2Model if existing object
        :param fail: None if success, CrossIdentificationException if fail
        """
        self.result: Layer2Model | None = result
        self.fail: CrossIdentificationException | None = fail


class CrossIdentificationException(BaseException):
    """
    Base cross identification exception
    """


class CrossIdentificationEmptyException(CrossIdentificationException):
    """Both coordinates and name provided are empty"""


class CrossIdentificationNamesNotFoundException(CrossIdentificationException):
    """Case, when only name known, but it has no matches in DB"""

    def __init__(self, names: list[str]):
        """
        :param names: Names, provided in raw table
        """
        self.names = names


class CrossIdentificationNamesDuplicateException(CrossIdentificationException):
    """Case, when provided names found for multiple objects in DB"""

    def __init__(self, names: list[str]):
        """
        :param names: Names, provided in raw table
        """
        self.names = names


class CrossIdentificationCoordCollisionException(CrossIdentificationException):
    """
    Describes collisions from cross identification use case
    """

    def __init__(self, target_param: CrossIdentificationParam, collisions: list[Layer2Model]):
        """
        :param target_param: The configuration, that caused collision
        :param collisions: The collided objects from DB
        """
        self.target_param: CrossIdentificationParam = target_param
        self.collisions: list[Layer2Model] = collisions


class CrossIdentificationNameCoordCollisionException(CrossIdentificationException):
    """
    Describes collision, when cross identified name and coordinates mismatch
    """

    def __init__(
        self, target_param: CrossIdentificationParam, name_hit: Layer2Model | None, coord_hit: Layer2Model | None
    ):
        """
        :param target_param: The configuration, that caused collision
        :param name_hit: Cross identification by name result
        :param coord_hit: Cross identification by coordinates result
        """
        self.target_param = target_param
        self.name_hit = name_hit
        self.coord_hit = coord_hit


class CrossIdentificationNameCoordFailException(CrossIdentificationException):
    """
    Describes collision, when both cross identification by name and by coordinates need user interaction
    """

    def __init__(
        self,
        target_param: CrossIdentificationParam,
        name_collision: CrossIdentificationException,
        coord_collision: CrossIdentificationException,
    ):
        """
        :param target_param: The configuration, that caused collision
        :param name_collision: Cross identification by name collision
        :param coord_collision: Cross identification by coordinates collision
        """
        self.target_param = target_param
        self.name_collision = name_collision
        self.coord_collision = coord_collision


class CrossIdentificationNameCoordCoordException(CrossIdentificationException):
    """
    Describes collision, name cross identification is successful, but coordinate cross identification needs user
    interaction
    """

    def __init__(
        self,
        target_param: CrossIdentificationParam,
        name_hit: Layer2Model | None,
        coord_collision: CrossIdentificationException,
    ):
        """
        :param target_param: The configuration, that caused collision
        :param name_hit: Cross identification by name result
        :param coord_collision: Cross identification by coordinates collision
        """
        self.target_param = target_param
        self.name_hit = name_hit
        self.coord_collision = coord_collision


class CrossIdentificationNameCoordNameFailException(CrossIdentificationException):
    """
    Describes collision, coordinate cross identification is successful, but name cross identification needs user
    interaction
    """

    def __init__(
        self,
        target_param: CrossIdentificationParam,
        name_collision: CrossIdentificationException,
        coord_hit: Layer2Model | None,
    ):
        """
        :param target_param: The configuration, that caused collision
        :param name_collision: Cross identification by name collision
        :param coord_hit: Cross identification by coordinates result
        """
        self.target_param = target_param
        self.name_collision = name_collision
        self.coord_hit = coord_hit


class CrossIdentificationDuplicateException(CrossIdentificationException):
    """
    When collision found between simultaneously processed objects
    """

    def __init__(
        self,
        target_param: CrossIdentificationParam,
        collisions: list[CrossIdentificationParam],
        db_cross_id_result: CrossIdentifyResult | CrossIdentificationCoordCollisionException,
    ):
        """
        :param target_param: The configuration, that caused collision
        :param collisions: Collisions with simultaneously processed objects
        :param db_cross_id_result: The result of cross identification with DB objects
        """
        self.target_param: CrossIdentificationParam = target_param
        self.collisions: list[CrossIdentificationParam] = collisions
        self.db_cross_id_result: CrossIdentifyResult | CrossIdentificationCoordCollisionException = db_cross_id_result
