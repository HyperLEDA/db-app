from dataclasses import dataclass

from app.data import model, repositories
from app.domain.processing import interface


@dataclass
class BatchKey:
    object_id: str
    ci_name: str

    def __str__(self) -> str:
        return f"{self.object_id}_{self.ci_name}"


def crossmatch(
    layer2_repo: repositories.Layer2Repository,
    objects: list[model.Layer0Object],
    designation_levenstein_threshold: int = 3,
    icrs_radius_threshold: float = 0.1,
) -> dict[str, set[int]]:
    """
    Performs the cross-identification of the objects. For each object layer 2 is queried to
    get the possible PGC numbers. All of the operations are performed in a single batch.

    If there are too many objects, the user of this function might want to query as many
    times as needed to avoid overflowing the memory.

    The behaviour of the processing may be customized with various options but it is safe to
    call it with default paramaters - they are determined sanely for most objects.

    Returns the mapping of the id of the object to the set of possible PGC numbers of this object.
    """
    cis = [
        interface.DesignationCI(designation_levenstein_threshold),
        interface.ICRSCI(icrs_radius_threshold),
    ]

    object_filters = {}

    for obj in objects:
        for ci in cis:
            filter_ = ci.get_filter(obj)

            if filter is not None:
                key = BatchKey(obj.object_id, ci.name())
                object_filters[key] = filter_

    objects_by_key = layer2_repo.query_batch(
        [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS],
        object_filters,
        limit=100,
        offset=0,
    )

    pgcs_by_ci: dict[str, dict[str, set[int]]] = {}

    for obj in objects:
        if obj.object_id not in pgcs_by_ci:
            pgcs_by_ci[obj.object_id] = {}

        for ci in cis:
            key = BatchKey(obj.object_id, ci.name())
            possible_objects = objects_by_key.get(str(key), [])

            pgcs = {o.pgc for o in possible_objects}
            pgcs_by_ci[obj.object_id][ci.name()] = pgcs

    result: dict[str, set[int]] = {}
    for obj_id, ci_pgcs in pgcs_by_ci.items():
        intersection = set.intersection(*ci_pgcs.values())

        result[obj_id] = intersection

    return result
