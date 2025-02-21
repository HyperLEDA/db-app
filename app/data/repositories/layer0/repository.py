import structlog

from app.data import model
from app.data.repositories.layer0 import objects, old_objects, tables
from app.lib.storage import enums, postgres


class Layer0Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

        self.table_repo = tables.Layer0TableRepository(storage)
        self.objects_repo = objects.Layer0ObjectRepository(storage)
        self.old_objects_repo = old_objects.Layer0OldObjectsRepository(storage)

    def create_table(self, data: model.Layer0TableMeta) -> model.Layer0CreationResponse:
        return self.table_repo.create_table(data)

    def insert_raw_data(self, data: model.Layer0RawData) -> None:
        return self.table_repo.insert_raw_data(data)

    def fetch_raw_data(
        self,
        table_id: int,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        offset: int = 0,
        limit: int | None = None,
    ) -> model.Layer0RawData:
        return self.table_repo.fetch_raw_data(table_id, columns, order_column, order_direction, offset, limit)

    def fetch_metadata(self, table_id: int) -> model.Layer0TableMeta:
        return self.table_repo.fetch_metadata(table_id)

    def update_column_metadata(self, table_id: int, column_description: model.ColumnDescription) -> None:
        return self.table_repo.update_column_metadata(table_id, column_description)

    def upsert_objects(
        self,
        table_id: int,
        objects: list[model.Layer0Object],
    ) -> None:
        return self.objects_repo.upsert_objects(table_id, objects)

    def upsert_old_object(
        self,
        table_id: int,
        processing_info: model.Layer0OldObject,
    ) -> None:
        return self.old_objects_repo.upsert_old_object(table_id, processing_info)

    def get_table_statistics(self, table_id: int) -> model.TableStatistics:
        return self.objects_repo.get_table_statistics(table_id)

    def get_old_object_statuses(self, table_id: int) -> dict[enums.ObjectCrossmatchStatus, int]:
        return self.old_objects_repo.get_old_object_statuses(table_id)

    def get_objects(self, table_id: int, limit: int, offset: int) -> list[model.Layer0Object]:
        return self.objects_repo.get_objects(table_id, limit, offset)

    def get_old_objects(self, table_id: int, batch_size: int, offset: int) -> list[model.Layer0OldObject]:
        return self.old_objects_repo.get_old_objects(table_id, batch_size, offset)

    def erase_crossmatch_results(self, table_id: int) -> None:
        return self.objects_repo.erase_crossmatch_results(table_id)
