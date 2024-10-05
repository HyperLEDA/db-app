from app import commands, entities, schema
from app.lib.storage import enums


def set_table_status(depot: commands.Depot, r: schema.SetTableStatusRequest) -> schema.SetTableStatusResponse:
    # TODO:
    # - Overrides to map object_id -> status, metadata
    # - Read objects table in batches
    # - Apply overrides
    # - Insert into PGC table
    # - Move to the layer1
    # - Update moved object statuses to processed
    overrides = {}

    for obj in r.overrides:
        if obj.pgc is not None:
            status = enums.ObjectProcessingStatus.EXISTING
            metadata = {"pgc": obj.pgc}
        else:
            status = enums.ObjectProcessingStatus.NEW
            metadata = {}

        overrides[obj.id] = (status, metadata)

    offset = 0

    while True:
        objects = depot.layer0_repo.get_objects(r.table_id, r.batch_size, offset)
        if len(objects) == 0:
            break

        for obj in objects:
            if obj.object_id in overrides:
                obj.status = overrides[obj.object_id][0]
                obj.metadata = overrides[obj.object_id][1]

        with depot.common_repo.with_tx():
            objects = assign_pgc(depot, objects)

    return schema.SetTableStatusResponse()


def assign_pgc(
    depot: commands.Depot, objects: list[entities.ObjectProcessingInfo]
) -> list[entities.ObjectProcessingInfo]:
    new_pgc_items_num = 0
    existing_pgc_items = []

    for obj in objects:
        if obj.status == enums.ObjectProcessingStatus.NEW:
            new_pgc_items_num += 1
        elif obj.status == enums.ObjectProcessingStatus.EXISTING:
            existing_pgc_items.append(obj.pgc)

    depot.common_repo.upsert_pgc(existing_pgc_items)
    pgc_list = depot.common_repo.generate_pgc(new_pgc_items_num)

    for obj in objects:
        if obj.status == enums.ObjectProcessingStatus.NEW:
            obj.pgc = pgc_list.pop(0)

    return objects
