from app import entities
from app.data import model, repositories
from app.domain.adminapi import cross_identification
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
        return adminapi.TableStatusStatsResponse(processing=self.layer0_repo.get_object_statuses(r.table_id))

    def table_process(self, r: adminapi.TableProcessRequest) -> adminapi.TableProcessResponse:
        return cross_identification.table_process_with_cross_identification(
            self.layer0_repo,
            self.layer2_repo,
            cross_identification.cross_identification,
            r,
        )

    def set_table_status(self, r: adminapi.SetTableStatusRequest) -> adminapi.SetTableStatusResponse:
        # TODO:
        # - Update moved object statuses to processed
        overrides = {}

        for obj in r.overrides or []:
            overrides[obj.id] = obj

        offset = 0

        while True:
            objects = self.layer0_repo.get_objects(r.table_id, r.batch_size, offset)

            for i, obj in enumerate(objects):
                if obj.object_id in overrides:
                    objects[i] = apply_override(objects[i], overrides[obj.object_id])

            with self.common_repo.with_tx():
                objects_to_move = assign_pgc(self.common_repo, objects)

                catalog_objects = []
                for obj in objects_to_move:
                    catalog_objects.extend(model.get_catalog_object(obj))

                self.layer1_repo.save_data(catalog_objects)

            if len(objects) < r.batch_size:
                break

        return adminapi.SetTableStatusResponse()


def apply_override(
    obj: entities.ObjectProcessingInfo,
    override: adminapi.SetTableStatusOverrides,
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
