import structlog
from astropy import table

from app.data import model
from app.data.repositories.layer0 import homogenization, objects, tables
from app.lib.storage import postgres


class Layer0Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

        self.table_repo = tables.Layer0TableRepository(storage)
        self.objects_repo = objects.Layer0ObjectRepository(storage)
        self.homogenization_repo = homogenization.Layer0HomogenizationRepository(storage)

    def create_table(self, data: model.Layer0TableMeta) -> model.Layer0CreationResponse:
        return self.table_repo.create_table(data)

    def insert_raw_data(self, data: model.Layer0RawData) -> None:
        return self.table_repo.insert_raw_data(data)

    def fetch_table(
        self,
        table_name: str,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
    ) -> table.Table:
        return self.table_repo.fetch_table(table_name, offset, columns, order_column, order_direction, limit)

    def fetch_raw_data(
        self,
        table_id: int,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
    ) -> model.Layer0RawData:
        return self.table_repo.fetch_raw_data(table_id, offset, columns, order_column, order_direction, limit)

    def fetch_metadata(self, table_id: int) -> model.Layer0TableMeta:
        return self.table_repo.fetch_metadata(table_id)

    def fetch_metadata_by_name(self, table_name: str) -> model.Layer0TableMeta:
        return self.table_repo.fetch_metadata_by_name(table_name)

    def update_column_metadata(self, table_name: str, column_description: model.ColumnDescription) -> None:
        return self.table_repo.update_column_metadata(table_name, column_description)

    def upsert_objects(self, table_id: int, objects: list[model.Layer0Object]) -> None:
        return self.objects_repo.upsert_objects(table_id, objects)

    def get_table_statistics(self, table_id: int) -> model.TableStatistics:
        return self.objects_repo.get_table_statistics(table_id)

    def get_objects(self, table_id: int, limit: int, offset: int) -> list[model.Layer0Object]:
        return self.objects_repo.get_objects(table_id, limit, offset)

    def get_processed_objects(
        self, table_id: int, limit: int, offset: str | None = None
    ) -> list[model.Layer0ProcessedObject]:
        return self.objects_repo.get_processed_objects(table_id, limit, offset)

    def erase_crossmatch_results(self, table_id: int) -> None:
        return self.objects_repo.erase_crossmatch_results(table_id)

    def add_crossmatch_result(self, data: dict[str, model.CIResult]) -> None:
        return self.objects_repo.add_crossmatch_result(data)

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        return self.objects_repo.upsert_pgc(pgcs)

    def get_homogenization_rules(self) -> list[model.HomogenizationRule]:
        return self.homogenization_repo.get_homogenization_rules()

    def get_homogenization_params(self) -> list[model.HomogenizationParams]:
        return self.homogenization_repo.get_homogenization_params()

    def add_homogenization_rules(self, rules: list[model.HomogenizationRule]) -> None:
        return self.homogenization_repo.add_homogenization_rules(rules)

    def add_homogenization_params(self, params: list[model.HomogenizationParams]) -> None:
        return self.homogenization_repo.add_homogenization_params(params)
