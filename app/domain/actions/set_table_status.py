from app import commands, entities, schema
from app.data import repositories
from app.lib.storage import enums


def set_table_status(depot: commands.Depot, r: schema.SetTableStatusRequest) -> schema.SetTableStatusResponse:
    # TODO:
    # - Move to the layer1
    # - Update moved object statuses to processed
    overrides = {}

    for obj in r.overrides:
        overrides[obj.id] = override_to_processing_info(obj)

    offset = 0

    while True:
        objects = depot.layer0_repo.get_objects(r.table_id, r.batch_size, offset)

        for i, obj in enumerate(objects):
            if obj.object_id in overrides:
                objects[i] = overrides[obj.object_id]

        with depot.common_repo.with_tx():
            objects_to_move = assign_pgc(depot.common_repo, objects)

            print(objects_to_move)

        if len(objects) < r.batch_size:
            break

    return schema.SetTableStatusResponse()


def override_to_processing_info(override: schema.SetTableStatusOverrides) -> entities.ObjectProcessingInfo:
    if override.pgc is not None:
        return entities.ObjectProcessingInfo(
            override.id, enums.ObjectProcessingStatus.EXISTING, {}, entities.ObjectInfo(), override.pgc
        )

    return entities.ObjectProcessingInfo(override.id, enums.ObjectProcessingStatus.NEW, {}, entities.ObjectInfo())


def assign_pgc(
    common_repo: repositories.CommonRepository, objects: list[entities.ObjectProcessingInfo]
) -> list[entities.ObjectProcessingInfo]:
    new_pgc_items_num = 0
    existing_pgc_items = []
    output_list = []

    for obj in objects:
        if obj.status == enums.ObjectProcessingStatus.NEW:
            new_pgc_items_num += 1
        elif obj.status == enums.ObjectProcessingStatus.EXISTING:
            existing_pgc_items.append(obj.pgc)
        else:
            continue

        output_list.append(obj)

    if len(existing_pgc_items) > 0:
        common_repo.upsert_pgc(existing_pgc_items)

    if new_pgc_items_num == 0:
        return output_list

    pgc_list = common_repo.generate_pgc(new_pgc_items_num)

    for obj in output_list:
        if obj.status == enums.ObjectProcessingStatus.NEW:
            obj.pgc = pgc_list.pop(0)

    return output_list
