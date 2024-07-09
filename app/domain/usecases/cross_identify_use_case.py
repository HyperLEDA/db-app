import astropy.units as u

from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model.layer2 import Layer2Model
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_dentification_user_param import CrossIdentificationUserParam
from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.model.params.layer_2_query_param import Layer2QueryByNames, Layer2QueryInCircle
from app.domain.repositories.layer_2_repository import Layer2Repository

DEFAULT_R1 = 1.5 * u.arcsec  # inner radius
DEFAULT_R2 = 1.5 * u.arcsec  # outer radius


class CrossIdentifyUseCase:
    """
    Finds an object by name or coordinates and returns it's id, or creates a new id, if it's a new object.
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
        if param.names is None and param.coordinates is None:
            return result.CrossIdentificationEmptyException()

        r1 = user_param.r1 if user_param.r1 is not None else DEFAULT_R1
        r2 = user_param.r2 if user_param.r2 is not None else DEFAULT_R2

        names_hit = None
        simultaneous_name_hit = []
        if param.names is not None:
            names_hit = await self._repository_l2.query_data(Layer2QueryByNames(param.names))
            simultaneous_name_hit = simultaneous_data_provider.by_name(param.names)

        coord_r1_hit = None
        coord_r2_hit = None
        simultaneous_r1_hit = []
        if param.coordinates is not None:
            coord_r1_hit = await self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r1))
            coord_r2_hit = await self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r2))
            simultaneous_r1_hit = simultaneous_data_provider.data_inside(param.coordinates, r1)

        if param.coordinates is not None and param.names is None:
            coord_res = self._only_coord_known(param, coord_r1_hit, coord_r2_hit)
        elif param.names is not None and param.coordinates is None:
            coord_res = self._only_names_known(param, names_hit)
        else:
            coord_res = self._name_and_coord_known(param, coord_r1_hit, coord_r2_hit, names_hit)

        if len(simultaneous_name_hit) > 1 or len(simultaneous_r1_hit) > 1:
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

    def _only_names_known(
        self, param: CrossIdentificationParam, names_hit: list[Layer2Model]
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException:
        """
        Case only name known
        :param param: Current identification param
        :param names_hit: Database entries with matching names
        :return: UseCase result
        """
        if len(names_hit) == 0:
            # no hits, pass object to user identification
            return result.CrossIdentificationNamesNotFoundException(param.names)

        if len(names_hit) == 1:
            # object identified in DB
            return result.CrossIdentifySuccess(names_hit[0])

        # else, names found for different objects
        return result.CrossIdentificationNamesDuplicateException(param.names)

    def _name_and_coord_known(
        self,
        param: CrossIdentificationParam,
        coord_r1: list[Layer2Model],
        coord_r2: list[Layer2Model],
        names_hit: list[Layer2Model],
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException:
        """
        Case name and coordinates known
        :param param: Current identification param
        :param coord_r1: Hits inside R1 in DB
        :param coord_r2: Hits inside R2 in DB
        :param names_hit: Database entry with matching name
        :return: UseCase result
        """

        names_res = self._only_names_known(param, names_hit)
        coord_res = self._only_coord_known(param, coord_r1, coord_r2)

        # name and coordinate cross identification success
        if isinstance(names_res, result.CrossIdentifySuccess) and isinstance(coord_res, result.CrossIdentifySuccess):
            if names_res.result is None and coord_res.result is None:
                # no hit by coordinates and name, new object
                return result.CrossIdentifySuccess(None)

            if (
                names_res.result is not None
                and coord_res.result is not None
                and names_res.result.pgc == coord_res.result.pgc
            ):
                # same hit by name and coordinates, object identified
                return result.CrossIdentifySuccess(names_res.result)

            # Different results for name and coordinates, error
            return result.CrossIdentificationNameCoordCollisionException(param, names_res.result, coord_res.result)

        if isinstance(names_res, result.CrossIdentificationException) and isinstance(
            coord_res, result.CrossIdentificationException
        ):
            # both coordinates and name cross identification results need user interaction
            return result.CrossIdentificationNameCoordFailException(param, names_res, coord_res)

        if isinstance(names_res, result.CrossIdentificationException):
            # name cross identification fail, coordinate cross identification success
            if isinstance(names_res, result.CrossIdentificationNamesNotFoundException):
                # special case, when we have no hits by name, but we can use coordinate result
                return result.CrossIdentifySuccess(coord_res.result)
            return result.CrossIdentificationNameCoordNameFailException(param, names_res, coord_res.result)

        # name cross identification success, coordinate cross identification fail
        return result.CrossIdentificationNameCoordCoordException(param, names_res.result, coord_res)
