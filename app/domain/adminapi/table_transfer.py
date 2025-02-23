from app.data import model, repositories
from app.domain import converters
from app.lib.storage import enums
from app.presentation import adminapi


class TableTransferManager:
    def __init__(
        self,
        common_repo: repositories.CommonRepository,
        layer0_repo: repositories.Layer0Repository,
        layer1_repo: repositories.Layer1Repository,
        layer2_repo: repositories.Layer2Repository,
    ) -> None:
        self.common_repo = common_repo
        self.layer0_repo = layer0_repo
        self.layer1_repo = layer1_repo
        self.layer2_repo = layer2_repo

    def table_status_stats(self, r: adminapi.TableStatusStatsRequest) -> adminapi.TableStatusStatsResponse:
        stats = self.layer0_repo.get_table_statistics(r.table_id)

        return adminapi.TableStatusStatsResponse(processing=stats.statuses)

    def table_process(self, r: adminapi.TableProcessRequest) -> adminapi.TableProcessResponse:
        meta = self.layer0_repo.fetch_metadata(r.table_id)

        convs: list[converters.QuantityConverter] = [
            converters.NameConverter(),
            converters.ICRSConverter(),
            converters.RedshiftConverter(),
        ]

        valid_converters = []

        for conv in convs:
            try:
                conv.parse_columns(meta.column_descriptions)
            except converters.ConverterError:
                continue

            valid_converters.append(conv)

        offset = 0

        while True:
            data = self.layer0_repo.fetch_raw_data(
                r.table_id, order_column=repositories.INTERNAL_ID_COLUMN_NAME, limit=r.batch_size, offset=offset
            )
            offset += min(r.batch_size, len(data.data))

            if len(data.data) == 0:
                break

            for obj_data in data.data.to_dict(orient="records"):
                objects: list[model.CatalogObject] = []
                for conv in valid_converters:
                    try:
                        obj = conv.apply(obj_data)
                    except converters.ConverterError:
                        continue

                    objects.append(obj)

                layer0_object = get_processing_info(obj_data[repositories.INTERNAL_ID_COLUMN_NAME], objects)

                # TODO: cross-identification

                self.layer0_repo.upsert_old_object(r.table_id, layer0_object)

        return adminapi.TableProcessResponse()

    def set_table_status(self, r: adminapi.SetTableStatusRequest) -> adminapi.SetTableStatusResponse:
        # TODO:
        # - Update moved object statuses to processed
        overrides = {}

        for obj in r.overrides or []:
            overrides[obj.id] = obj

        offset = 0

        while True:
            objects = self.layer0_repo.get_old_objects(r.table_id, r.batch_size, offset)

            for i, obj in enumerate(objects):
                if obj.object_id in overrides:
                    objects[i] = apply_override(objects[i], overrides[obj.object_id])

            with self.common_repo.with_tx():
                objects_to_move = assign_pgc(self.common_repo, objects)

                catalog_objects: list[model.Layer1CatalogObject] = []
                for obj in objects_to_move:
                    for catalog_object in obj.data:
                        catalog_objects.append(
                            model.Layer1CatalogObject(obj.pgc, obj.object_id, catalog_object),
                        )

                self.layer1_repo.save_data(catalog_objects)

            offset += r.batch_size

            if len(objects) < r.batch_size:
                break

        return adminapi.SetTableStatusResponse()


def get_processing_info(object_id: str, data: list[model.CatalogObject]) -> model.Layer0OldObject:
    """
    :param object_id: Internal ID of the object
    :param res: Object that stores data about the cross identification processing
    :param obj: Processed and homogenous information about the object
    """
    return model.Layer0OldObject(object_id, enums.ObjectCrossmatchStatus.NEW, {}, data)


def apply_override(
    obj: model.Layer0OldObject,
    override: adminapi.SetTableStatusOverrides,
) -> model.Layer0OldObject:
    if override.pgc is not None:
        obj.status = enums.ObjectCrossmatchStatus.EXISTING
        obj.pgc = override.pgc
    else:
        obj.status = enums.ObjectCrossmatchStatus.NEW
        obj.pgc = None

    return obj


def assign_pgc(
    common_repo: repositories.CommonRepository, objects: list[model.Layer0OldObject]
) -> list[model.Layer0OldObject]:
    new_pgc_items_num = 0
    existing_pgc_items = []
    output_list = []

    for obj in objects:
        if obj.status == enums.ObjectCrossmatchStatus.NEW:
            new_pgc_items_num += 1
        elif obj.status == enums.ObjectCrossmatchStatus.EXISTING:
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
        if obj.status == enums.ObjectCrossmatchStatus.NEW:
            obj.pgc = pgc_list.pop(0)

    return output_list
