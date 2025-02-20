from collections.abc import Iterable
from dataclasses import dataclass

from app.data import model, repositories
from app.domain.processing import interface


@dataclass
class CIResultObjectNew:
    pass


@dataclass
class CIResultObjectExisting:
    pgc: int


@dataclass
class CIResultObjectCollision:
    possible_pgcs: set[int]


CIResult = CIResultObjectNew | CIResultObjectExisting | CIResultObjectCollision


@dataclass
class BatchKey:
    object_id: str
    ci_name: str

    def __str__(self) -> str:
        return f"{self.object_id}_{self.ci_name}"


def query_objects(
    layer2_repo: repositories.Layer2Repository,
    objects: list[model.Layer0Object],
    crossmatchers: list[interface.Crossmatcher],
) -> dict[str, dict[str, set[int]]]:
    object_filters = {}

    for obj in objects:
        for cm in crossmatchers:
            filter_ = cm.get_filter(obj)

            if filter_ is not None:
                key = BatchKey(obj.object_id, cm.name())
                object_filters[key] = filter_

    flat_result = layer2_repo.query_batch(
        [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS],
        object_filters,
        limit=100,
        offset=0,
    )

    result: dict[str, dict[str, set[int]]] = {}

    for obj in objects:
        if obj.object_id not in result:
            result[obj.object_id] = {}

        for cm in crossmatchers:
            key = BatchKey(obj.object_id, cm.name())
            possible_objects = flat_result.get(str(key), [])

            pgcs = {o.pgc for o in possible_objects}
            result[obj.object_id][cm.name()] = pgcs

    return result


def compute_ci_result(possible_pgcs: Iterable[set[int]]) -> CIResult:
    """
    If all of the CIs returned zero PGCs, then object is `new`.

    Otherwise, if the intersection between all CI results is of length 1, object is `existing`.

    In all other cases, there is a `collision`.
    """

    union = set.union(*possible_pgcs)
    if len(union) == 0:
        return CIResultObjectNew()

    intersection = set.intersection(*possible_pgcs)

    if len(intersection) == 1:
        return CIResultObjectExisting(intersection.pop())

    return CIResultObjectCollision(union)


def crossmatch(
    layer2_repo: repositories.Layer2Repository,
    objects: list[model.Layer0Object],
    designation_levenshtein_threshold: int = 3,
    icrs_radius_threshold_deg: float = 0.1,
) -> dict[str, CIResult]:
    """
    Performs the cross-identification of the objects. For each object layer 2 is queried to
    get the possible PGC numbers. All of the operations are performed in a single batch.

    If there are too many objects, the user of this function might want to query in batches as many
    times as needed to avoid overflowing the memory.

    The behaviour of the processing may be customized with various options but it is safe to
    call it with default paramaters - they are determined sanely for most objects.

    Returns the mapping of the id of the object to the set of possible PGC numbers of this object.
    """
    crossmatchers: list[interface.Crossmatcher] = [
        interface.DesignationCrossmatcher(designation_levenshtein_threshold),
        interface.ICRSCrossmatcher(icrs_radius_threshold_deg),
    ]

    layer2_objects = query_objects(layer2_repo, objects, crossmatchers)

    result: dict[str, CIResult] = {}
    for obj_id, ci_pgcs in layer2_objects.items():
        result[obj_id] = compute_ci_result(ci_pgcs.values())

    return result
