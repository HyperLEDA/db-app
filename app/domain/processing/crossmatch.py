from dataclasses import dataclass

from app.data import model, repositories
from app.domain.processing import interface


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
):
    object_filters = {}

    for obj in objects:
        for cm in crossmatchers:
            filter_ = cm.get_filter(obj)

            if filter_ is not None:
                key = BatchKey(obj.object_id, cm.name())
                object_filters[key] = filter_

    return layer2_repo.query_batch(
        [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS],
        object_filters,
        limit=100,
        offset=0,
    )


def match_pgc(
    layer0_objects: list[model.Layer0Object],
    layer2_objects: dict[str, list[model.Layer2Object]],
    crossmatchers: list[interface.Crossmatcher],
) -> dict[str, set[int]]:
    pgcs_by_cm: dict[str, dict[str, set[int]]] = {}

    for obj in layer0_objects:
        if obj.object_id not in pgcs_by_cm:
            pgcs_by_cm[obj.object_id] = {}

        for cm in crossmatchers:
            key = BatchKey(obj.object_id, cm.name())
            possible_objects = layer2_objects.get(str(key), [])

            pgcs = {o.pgc for o in possible_objects}
            pgcs_by_cm[obj.object_id][cm.name()] = pgcs

    result: dict[str, set[int]] = {}
    for obj_id, ci_pgcs in pgcs_by_cm.items():
        intersection = set.intersection(*ci_pgcs.values())

        result[obj_id] = intersection

    return result


def crossmatch(
    layer2_repo: repositories.Layer2Repository,
    objects: list[model.Layer0Object],
    designation_levenshtein_threshold: int = 3,
    icrs_radius_threshold_deg: float = 0.1,
) -> dict[str, set[int]]:
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

    objects_by_key = query_objects(layer2_repo, objects, crossmatchers)

    return match_pgc(objects, objects_by_key, crossmatchers)
