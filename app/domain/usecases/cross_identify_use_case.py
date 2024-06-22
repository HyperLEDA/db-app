import astropy.units as u

from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model.layer2 import Layer2Model
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_dentification_user_param import CrossIdentificationUserParam
from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.model.params.layer_2_query_param import Layer2QueryByName, Layer2QueryInCircle
from app.domain.repositories.layer_2_repository import Layer2Repository

default_r1 = 1.5 * u.arcsec  # inner radius
default_r2 = 1.5 * u.arcsec  # outer radius


class CrossIdentifyUseCase:
    """
    Finds an object by name or coordinates and return's it's id, or creates a new id, if it's a new object.
    If there is a collision, returns this collision description
    """

    def __init__(self, repository_l2: Layer2Repository):
        self._repository_l2: Layer2Repository = repository_l2

    async def invoke(
        self,
        param: CrossIdentificationParam,
        simultaneous_data_provider: CrossIdSimultaneousDataProvider,
        user_param: CrossIdentificationUserParam,
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException:
        """
        :param param: Data, used to identify object
        :param simultaneous_data_provider: Provides data about objects, processed simultaneously to this
        :param user_param: User defined parameters for cross identification
        :return: id for this object
        """
        if param.name is None and param.coordinates is None:
            return result.CrossIdentificationEmptyException()

        r1 = user_param.r1 if user_param.r1 is not None else default_r1
        r2 = user_param.r2 if user_param.r2 is not None else default_r2

        name_hit = None
        simultaneous_name_hit = []
        if param.name is not None:
            name_query_res = await self._repository_l2.query_data(Layer2QueryByName(param.name))
            if len(name_query_res) == 1:
                name_hit = name_query_res[0]
            simultaneous_name_hit = simultaneous_data_provider.by_name(param.name)

        coord_r1_hit = None
        coord_r2_hit = None
        simultaneous_r1_hit = []
        if param.coordinates is not None:
            coord_r1_hit = await self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r1))
            coord_r2_hit = await self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r2))
            simultaneous_r1_hit = simultaneous_data_provider.data_inside(param.coordinates, r1)

        if param.coordinates is not None and param.name is None:
            coord_res = self._only_coord_known(param, coord_r1_hit, coord_r2_hit)
        elif param.name is not None and param.coordinates is None:
            coord_res = self._only_name_known(param, name_hit)
        else:
            coord_res = self._name_and_coord_known(param, coord_r1_hit, coord_r2_hit, name_hit)

        if len(simultaneous_name_hit) > 0 or len(simultaneous_r1_hit) > 1:
            return result.CrossIdentificationDuplicateException(
                param, simultaneous_name_hit + simultaneous_r1_hit, coord_res
            )

        return coord_res

    def _only_coord_known(
        self,
        param: CrossIdentificationParam,
        coord_r1: list[Layer2Model],
        coord_r2: list[Layer2Model],
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException:
        """
        Case, where only coordinates of the queried object are known
        :param param: Current identification param
        :param coord_r1: Hits inside R1 in DB
        :param coord_r2: Hits inside R2 in DB
        :return: UseCase result
        """

        # no hits, new objects
        if len(coord_r2) == 0:
            return result.CrossIdentifySuccess(None)

        # exactly one hit, object identified
        if len(coord_r1) == 1 and len(coord_r2) == 1:
            return result.CrossIdentifySuccess(coord_r1[0])

        # potential collision
        if len(coord_r2) > 1:
            return result.CrossIdentificationCoordCollisionException(param, coord_r2)

        raise ValueError(f"Unexpected R1 and R2 query results: len(r1) = {len(coord_r1)}, len(r2) = {len(coord_r2)}")

    def _only_name_known(
        self, param: CrossIdentificationParam, name_hit: Layer2Model | None
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException:
        """
        Case only name known
        :param param: Current identification param
        :param name_hit: Database entry with matching name
        :return: UseCase result
        """
        if name_hit is not None:
            return result.CrossIdentifySuccess(name_hit)

        return result.CrossIdentifySuccess(None)

    def _name_and_coord_known(
        self,
        param: CrossIdentificationParam,
        coord_r1: list[Layer2Model],
        coord_r2: list[Layer2Model],
        name_hit: Layer2Model | None,
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException:
        """
        Case name and coordinates known
        :param param: Current identification param
        :param coord_r1: Hits inside R1 in DB
        :param coord_r2: Hits inside R2 in DB
        :param name_hit: Database entry with matching name
        :return: UseCase result
        """

        name_res = self._only_name_known(param, name_hit)
        coord_res = self._only_coord_known(param, coord_r1, coord_r2)

        # name and coordinate cross identification success
        if isinstance(name_res, result.CrossIdentifySuccess) and isinstance(coord_res, result.CrossIdentifySuccess):
            if name_res.result is None and coord_res.result is None:
                # no hit by coordinates and name, new object
                return result.CrossIdentifySuccess(None)

            if (
                name_res.result is not None
                and coord_res.result is not None
                and name_res.result.pgc == coord_res.result.pgc
            ):
                # same hit by name and coordinates, object identified
                return result.CrossIdentifySuccess(name_res.result)

            # Different results for name and coordinates, error
            return result.CrossIdentificationNameCoordCollisionException(param, name_res.result, coord_res.result)

        if isinstance(name_res, result.CrossIdentificationException) and isinstance(
            coord_res, result.CrossIdentificationException
        ):
            # both coordinates and name cross identification results need user interaction
            return result.CrossIdentificationNameCoordFailException(param, name_res, coord_res)

        if isinstance(name_res, result.CrossIdentificationException):
            # name cross identification fail, coordinate cross identification success
            return result.CrossIdentificationNameCoordNameFailException(param, name_res, coord_res.result)

        # name cross identification success, coordinate cross identification fail
        return result.CrossIdentificationNameCoordCoordException(param, name_res.result, coord_res)
