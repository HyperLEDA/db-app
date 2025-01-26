from app import commands, entities, schema
from app.data import model, repositories
from app.lib.storage import enums


def set_table_status(depot: commands.Depot, r: schema.SetTableStatusRequest) -> schema.SetTableStatusResponse:
    # TODO:
    # - Update moved object statuses to processed
    overrides = {}

    for obj in r.overrides or []:
        overrides[obj.id] = obj

    offset = 0

    while True:
        objects = depot.layer0_repo.get_objects(r.batch_size, offset)

        for i, obj in enumerate(objects):
            if obj.object_id in overrides:
                objects[i] = apply_override(objects[i], overrides[obj.object_id])

        with depot.common_repo.with_tx():
            objects_to_move = assign_pgc(depot.common_repo, objects)

            catalog_objects = []
            for obj in objects_to_move:
                catalog_objects.extend(to_catalog_object(obj))

            depot.layer1_repo.save_data(catalog_objects)

        if len(objects) < r.batch_size:
            break

    return schema.SetTableStatusResponse()


def to_catalog_object(obj: entities.ObjectProcessingInfo) -> list[model.CatalogObject]:
    return [
        model.DesignationCatalogObject(obj.pgc, obj.object_id, designation=obj.data.primary_name),
        model.ICRSCatalogObject(
            obj.pgc,
            obj.object_id,
            ra=obj.data.coordinates.ra.deg,
            dec=obj.data.coordinates.dec.deg,
            e_ra=0.01,
            e_dec=0.02,
        ),
    ]


def apply_override(
    obj: entities.ObjectProcessingInfo,
    override: schema.SetTableStatusOverrides,
) -> entities.ObjectProcessingInfo:
    if override.pgc is not None:
        obj.status = enums.ObjectProcessingStatus.EXISTING
        obj.pgc = override.pgc
    else:
        obj.status = enums.ObjectProcessingStatus.NEW
        obj.pgc = None

    return obj


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
