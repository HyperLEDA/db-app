import astropy.units as u
from astropy.coordinates import Angle

from app.domain.cross_id_simultaneous_data_provider import CrossIdSimultaneousDataProvider
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_dentification_user_param import CrossIdentificationUserParam
from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.model.params.layer_2_query_param import Layer2QueryByNames, Layer2QueryInCircle
from app.domain.repositories.layer_2_repository import Layer2Repository

INNER_RADIUS = 1.5 * u.arcsec  # default inner radius
OUTER_RADIUS = 4.5 * u.arcsec  # default outer radius


class CrossIdentifyUseCase:
    """
    Finds an object by name or coordinates and returns it's id, or creates a new id, if it's a new object.
    If there is a collision, returns this collision description
    """

    def __init__(self, repository_l2: Layer2Repository):
        self._repository_l2: Layer2Repository = repository_l2

    def invoke(
        self,
        param: CrossIdentificationParam,
        simultaneous_data_provider: CrossIdSimultaneousDataProvider,
        user_param: CrossIdentificationUserParam,
    ) -> result.CrossIdentifyResult:
        """
        :param param: Data, used to identify object
        :param simultaneous_data_provider: Provides data about objects, processed simultaneously to this
        :param user_param: User defined parameters for cross identification
        :return: Result, containing identification result or fail description
        """
        if param.names is None and param.coordinates is None:
            return result.CrossIdentifyResult(None, result.CrossIdentificationEmptyException())

        r1 = user_param.r1 if user_param.r1 is not None else INNER_RADIUS
        r2 = user_param.r2 if user_param.r2 is not None else OUTER_RADIUS

        simultaneous_name_hit = []
        if param.names is not None:
            simultaneous_name_hit = simultaneous_data_provider.by_name(param.names)

        simultaneous_r1_hit = []
        if param.coordinates is not None:
            simultaneous_r1_hit = simultaneous_data_provider.data_inside(param.coordinates, r1)

        coord_res = None
        if param.coordinates is not None:
            coord_res = self._identify_by_coordinates(param, r1, r2)

        names_res = None
        if param.names is not None:
            names_res = self._identify_by_names(param)

        res = self._compile_results(param, coord_res, names_res)

        if len(simultaneous_name_hit) > 1 or len(simultaneous_r1_hit) > 1:
            return result.CrossIdentifyResult(
                None,
                result.CrossIdentificationDuplicateException(param, simultaneous_name_hit + simultaneous_r1_hit, res)
            )

        return res

    def _identify_by_coordinates(
        self,
        param: CrossIdentificationParam,
        r1: Angle,
        r2: Angle,
    ) -> result.CrossIdentifyResult:
        """
        Cross identification by coordinates
        :param param: Current identification param
        :param r1: Inner radius
        :param r2: Outer radius
        :return: UseCase result
        """

        r1_hit = self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r1))
        r2_hit = self._repository_l2.query_data(Layer2QueryInCircle(param.coordinates, r2))

        # no hits, new objects
        if len(r2_hit) == 0:
            return result.CrossIdentifyResult(None, None)

        # exactly one hit, object identified
        if len(r1_hit) == 1 and len(r2_hit) == 1:
            return result.CrossIdentifyResult(r1_hit[0], None)

        # potential collision
        if len(r2_hit) > 1:
            return result.CrossIdentifyResult(None, result.CrossIdentificationCoordCollisionException(param, r2_hit))

        raise ValueError(f"Unexpected R1 and R2 query results: len(r1) = {len(r1_hit)}, len(r2) = {len(r2_hit)}")

    def _identify_by_names(
        self, param: CrossIdentificationParam
    ) -> result.CrossIdentifyResult:
        """
        Cross identification by names
        :param param: Current identification param
        :return: UseCase result
        """

        names_hit = self._repository_l2.query_data(Layer2QueryByNames(param.names))

        if len(names_hit) == 0:
            # no hits, pass object to user identification
            return result.CrossIdentifyResult(None, result.CrossIdentificationNamesNotFoundException(param.names))

        if len(names_hit) == 1:
            # object identified in DB
            return result.CrossIdentifyResult(names_hit[0], None)

        # else, names found for different objects
        return result.CrossIdentifyResult(None, result.CrossIdentificationNamesDuplicateException(param.names))

    def _compile_results(
        self,
        param: CrossIdentificationParam,
        coord_res: result.CrossIdentifyResult | result.CrossIdentificationException | None,
        names_res: result.CrossIdentifyResult | result.CrossIdentificationException | None,
    ) -> result.CrossIdentifyResult:
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
        if names_res.fail is None and coord_res.fail is None:
            if names_res.result is None and coord_res.result is None:
                # no hit by coordinates and name, new object
                return result.CrossIdentifyResult(None, None)

            if (
                names_res.result is not None
                and coord_res.result is not None
                and names_res.result.pgc == coord_res.result.pgc
            ):
                # same hit by name and coordinates, object identified
                return result.CrossIdentifyResult(names_res.result, None)

            # Different results for name and coordinates, error
            return result.CrossIdentifyResult(
                None,
                result.CrossIdentificationNameCoordCollisionException(param, names_res.result, coord_res.result)
            )

        if names_res.fail is not None and coord_res.fail is not None:
            # both coordinates and name cross identification results need user interaction
            return result.CrossIdentifyResult(
                None,
                result.CrossIdentificationNameCoordFailException(param, names_res.fail, coord_res.fail)
            )

        if names_res.fail is not None:
            # name cross identification fail, coordinate cross identification success
            if isinstance(names_res.fail, result.CrossIdentificationNamesNotFoundException):
                # special case, when we have no hits by name, but we can use coordinate result
                return result.CrossIdentifyResult(coord_res.result, None)
            return result.CrossIdentifyResult(
                None,
                result.CrossIdentificationNameCoordNameFailException(param, names_res.fail, coord_res.result)
            )

        # name cross identification success, coordinate cross identification fail
        return result.CrossIdentifyResult(
            None,
            result.CrossIdentificationNameCoordCoordException(param, names_res.result, coord_res)
        )
