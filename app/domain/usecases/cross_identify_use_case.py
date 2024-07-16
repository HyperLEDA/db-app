import astropy.units as u
from astropy.coordinates import Angle

from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_dentification_user_param import CrossIdentificationUserParam
from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.model.params.layer_2_query_param import Layer2QueryByNames, Layer2QueryInCircle
from app.domain.repositories.layer_2_repository import Layer2Repository

INNER_RADIUS = 1.5 * u.arcsec  # default inner radius
OUTER_RADIUS = 1.5 * u.arcsec  # default outer radius


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

        r1 = user_param.r1 if user_param.r1 is not None else INNER_RADIUS
        r2 = user_param.r2 if user_param.r2 is not None else OUTER_RADIUS

        simultaneous_name_hit = []
        if param.names is not None:
            simultaneous_name_hit = simultaneous_data_provider.by_name(param.names)

        simultaneous_r1_hit = []
        if param.coordinates is not None:
            simultaneous_r1_hit = simultaneous_data_provider.data_inside(param.coordinates, r1)

        coord_res = await self._identify_by_coordinates(param, r1, r2)
        names_res = await self._identify_by_names(param)

        res = self._compile_results(param, coord_res, names_res)

        if len(simultaneous_name_hit) > 1 or len(simultaneous_r1_hit) > 1:
            return result.CrossIdentificationDuplicateException(param, simultaneous_name_hit + simultaneous_r1_hit, res)

        return res

    async def _identify_by_coordinates(
        self,
        param: CrossIdentificationParam,
        r1: Angle,
        r2: Angle,
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException | None:
        """
        Cross identification by coordinates
        :param param: Current identification param
        :param r1: Inner radius
        :param r2: Outer radius
        :return: UseCase result or None if not enough info
        """

        # Not enough info for identification by coordinates
        if param.coordinates is None:
            return None

        r1_hit = await self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r1))
        r2_hit = await self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r2))

        # no hits, new objects
        if len(r2_hit) == 0:
            return result.CrossIdentifySuccess(None)

        # exactly one hit, object identified
        if len(r1_hit) == 1 and len(r2_hit) == 1:
            return result.CrossIdentifySuccess(r1_hit[0])

        # potential collision
        if len(r2_hit) > 1:
            return result.CrossIdentificationCoordCollisionException(param, r2_hit)

        raise ValueError(f"Unexpected R1 and R2 query results: len(r1) = {len(r1_hit)}, len(r2) = {len(r2_hit)}")

    async def _identify_by_names(
        self, param: CrossIdentificationParam
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException | None:
        """
        Cross identification by names
        :param param: Current identification param
        :return: UseCase result or None if not enough info
        """

        # Not enough info for identification by names
        if param.names is None:
            return None

        names_hit = await self._repository_l2.query_data(Layer2QueryByNames(param.names))

        if len(names_hit) == 0:
            # no hits, pass object to user identification
            return result.CrossIdentificationNamesNotFoundException(param.names)

        if len(names_hit) == 1:
            # object identified in DB
            return result.CrossIdentifySuccess(names_hit[0])

        # else, names found for different objects
        return result.CrossIdentificationNamesDuplicateException(param.names)

    def _compile_results(
        self,
        param: CrossIdentificationParam,
        coord_res: result.CrossIdentifySuccess | result.CrossIdentificationException | None,
        names_res: result.CrossIdentifySuccess | result.CrossIdentificationException | None,
    ) -> result.CrossIdentifySuccess | result.CrossIdentificationException:
        """
        Compile results of name and coordinates cross identification
        :param param: Current identification param
        :param coord_res: Result of identification by coordinates
        :param names_res: Result of identification by names
        :return: UseCase result
        """
        if coord_res is None:
            return names_res
        if names_res is None:
            return coord_res

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
