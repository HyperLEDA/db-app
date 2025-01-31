from collections.abc import Callable

import astropy.units as u
from astropy.coordinates import ICRS, Angle

from app import entities
from app.data import repositories
from app.domain import converters
from app.domain.cross_id_simultaneous_data_provider import (
    CrossIdSimultaneousDataProvider,
    SimpleSimultaneousDataProvider,
)
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_identification_user_param import CrossIdentificationUserParam
from app.lib.storage import enums
from app.lib.web import errors
from app.presentation import adminapi

DEFAULT_INNER_RADIUS = 1.5 * u.arcsec
DEFAULT_OUTER_RADIUS = 4.5 * u.arcsec

cross_identification_func_type = Callable[
    [
        repositories.Layer2Repository,
        entities.ObjectInfo,
        CrossIdSimultaneousDataProvider,
        CrossIdentificationUserParam,
    ],
    result.CrossIdentifyResult,
]


def table_process_with_cross_identification(
    layer0_repo: repositories.Layer0Repository,
    layer2_repo: repositories.Layer2Repository,
    cross_identification_func: cross_identification_func_type,
    r: adminapi.TableProcessRequest,
) -> adminapi.TableProcessResponse:
    meta = layer0_repo.fetch_metadata(r.table_id)

    converter = converters.CompositeConverter(
        converters.NameConverter(),
        converters.ICRSConverter(),
    )

    try:
        converter.parse_columns(meta.column_descriptions)
    except converters.ConverterError as e:
        raise errors.LogicalError(f"Unable to process table: {str(e)}") from e

    offset = 0

    while True:
        data = layer0_repo.fetch_raw_data(
            r.table_id, order_column=repositories.INTERNAL_ID_COLUMN_NAME, limit=r.batch_size, offset=offset
        )
        offset += min(r.batch_size, len(data.data))

        if len(data.data) == 0:
            break

        for obj_data in data.data.to_dict(orient="records"):
            obj = converter.apply(entities.ObjectInfo(), obj_data)

            result = cross_identification_func(
                layer2_repo,
                obj,
                SimpleSimultaneousDataProvider([]),  # TODO: use correct provider
                CrossIdentificationUserParam(
                    r.cross_identification.inner_radius_arcsec * u.arcsec,
                    r.cross_identification.outer_radius_arcsec * u.arcsec,
                ),
            )

            processing_info = get_processing_info(obj_data[repositories.INTERNAL_ID_COLUMN_NAME], result, obj)
            layer0_repo.upsert_object(r.table_id, processing_info)

    # TODO: remove col_name and coordinate_part from entities?

    return adminapi.TableProcessResponse()


def get_processing_info(
    object_id: str,
    res: result.CrossIdentifyResult,
    obj: entities.ObjectInfo,
) -> entities.ObjectProcessingInfo:
    """
    :param object_id: Internal ID of the object
    :param res: Object that stores data about the cross identification processing
    :param obj: Processed and homogenous information about the object
    """
    if res.fail is None:
        if res.result is None:
            return entities.ObjectProcessingInfo(object_id, enums.ObjectProcessingStatus.NEW, {}, obj)

        return entities.ObjectProcessingInfo(object_id, enums.ObjectProcessingStatus.EXISTING, {}, obj, res.result.pgc)

    return entities.ObjectProcessingInfo(object_id, enums.ObjectProcessingStatus.COLLIDED, {"error": res.fail}, obj)


def cross_identification(
    layer2_repo: repositories.Layer2Repository,
    param: entities.ObjectInfo,
    simultaneous_data_provider: CrossIdSimultaneousDataProvider,
    user_param: CrossIdentificationUserParam,
) -> result.CrossIdentifyResult:
    """
    :param param: Data, used to identify object
    :param simultaneous_data_provider: Provides data about objects, processed simultaneously to this
    :param user_param: User defined parameters for cross identification
    :return: Result, containing identification result or fail description

    Finds an object by name or coordinates and returns its id, or creates a new id, if it is a new object.
    If there is a collision, returns this collision description.
    """
    if param.names is None and param.coordinates is None:
        return result.CrossIdentifyResult(None, result.CrossIdentificationEmptyException())

    r1 = user_param.r1 if user_param.r1 is not None else DEFAULT_INNER_RADIUS
    r2 = user_param.r2 if user_param.r2 is not None else DEFAULT_OUTER_RADIUS

    simultaneous_r1_hit = []
    coord_res = None
    if param.coordinates is not None:
        simultaneous_r1_hit = simultaneous_data_provider.data_inside(param.coordinates, r1)
        coord_res = _identify_by_coordinates(layer2_repo, param.coordinates, r1, r2)

    simultaneous_name_hit = []
    names_res = None
    if param.names is not None:
        simultaneous_name_hit = simultaneous_data_provider.by_name(param.names)
        names_res = _identify_by_names(layer2_repo, param.names)

    res = _compile_results(param, coord_res, names_res)

    if len(simultaneous_name_hit) > 1 or len(simultaneous_r1_hit) > 1:
        return result.CrossIdentifyResult(
            None,
            result.CrossIdentificationDuplicateException(param, simultaneous_name_hit + simultaneous_r1_hit, res),
        )

    return res


def _identify_by_coordinates(
    layer2_repo: repositories.Layer2Repository,
    coordinates: ICRS,
    inner_r: Angle,
    outer_r: Angle,
) -> result.CrossIdentifyResult:
    """
    Cross identification by coordinates

    :param coordinates: Sky koordinates of identified object
    :param inner_r: Inner radius
    :param outer_r: Outer radius
    :return: UseCase result
    """

    r1_hit = []  # layer2_repo.query_data(Layer2QueryInCircle(coordinates, inner_r))
    r2_hit = []  # layer2_repo.query_data(Layer2QueryInCircle(coordinates, outer_r))

    # no hits, new objects
    if len(r2_hit) == 0:
        return result.CrossIdentifyResult(None, None)

    # exactly one hit, object identified
    if len(r1_hit) == 1 and len(r2_hit) == 1:
        return result.CrossIdentifyResult(r1_hit[0], None)

    # potential collision
    if len(r2_hit) > 1:
        return result.CrossIdentifyResult(
            None, result.CrossIdentificationCoordCollisionException(coordinates, inner_r, outer_r, r2_hit)
        )

    raise ValueError(f"Unexpected R1 and R2 query results: len(r1) = {len(r1_hit)}, len(r2) = {len(r2_hit)}")


def _identify_by_names(layer2_repo: repositories.Layer2Repository, names: list[str]) -> result.CrossIdentifyResult:
    """
    Cross identification by names

    :param names: Names to identify
    :return: UseCase result
    """

    names_hit = []

    if len(names_hit) == 0:
        # no hits, pass object to user identification
        return result.CrossIdentifyResult(None, result.CrossIdentificationNamesNotFoundException(names))

    if len(names_hit) == 1:
        # object identified in DB
        return result.CrossIdentifyResult(names_hit[0], None)

    # else, names found for different objects
    return result.CrossIdentifyResult(None, result.CrossIdentificationNamesDuplicateException(names))


def _compile_results(
    param: entities.ObjectInfo,
    coord_res: result.CrossIdentifyResult | None,
    names_res: result.CrossIdentifyResult | None,
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
            None, result.CrossIdentificationNameCoordCollisionException(param, names_res.result, coord_res.result)
        )

    if names_res.fail is not None and coord_res.fail is not None:
        # both coordinates and name cross identification results need user interaction
        return result.CrossIdentifyResult(
            None, result.CrossIdentificationNameCoordFailException(param, names_res.fail, coord_res.fail)
        )

    if names_res.fail is not None:
        # name cross identification fail, coordinate cross identification success
        if isinstance(names_res.fail, result.CrossIdentificationNamesNotFoundException):
            # special case, when we have no hits by name, but we can use coordinate result
            return result.CrossIdentifyResult(coord_res.result, None)
        return result.CrossIdentifyResult(
            None, result.CrossIdentificationNameCoordNameFailException(param, names_res.fail, coord_res.result)
        )

    # name cross identification success, coordinate cross identification fail
    return result.CrossIdentifyResult(
        None, result.CrossIdentificationNameCoordCoordException(param, names_res.result, coord_res.fail)
    )
