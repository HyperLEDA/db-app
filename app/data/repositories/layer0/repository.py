from collections.abc import Sequence

import structlog
from astropy import table

from app.data import model
from app.data.repositories.layer0 import records, tables
from app.lib.storage import enums, postgres


class Layer0Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

        self.table_repo = tables.Layer0TableRepository(storage)
        self.records_repo = records.Layer0RecordRepository(storage)

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
        table_name: str | None = None,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
        record_id: str | None = None,
        row_offset: int | None = None,
    ) -> model.Layer0RawData:
        return self.table_repo.fetch_raw_data(
            table_name,
            offset,
            columns,
            order_column,
            order_direction,
            limit,
            record_id,
            row_offset,
        )

    def fetch_records(
        self,
        table_name: str,
        limit: int,
        row_offset: int,
        order_direction: str = "asc",
        has_pgc: bool | None = None,
        pgc_value: int | None = None,
        triage_status: str | None = None,
    ) -> list[model.TableRecord]:
        return self.table_repo.fetch_records(
            table_name, limit, row_offset, order_direction, has_pgc, pgc_value, triage_status
        )

    def fetch_metadata(self, table_name: str) -> model.Layer0TableMeta:
        return self.table_repo.fetch_metadata(table_name)

    def fetch_metadata_by_name(self, table_name: str) -> model.Layer0TableMeta:
        return self.table_repo.fetch_metadata_by_name(table_name)

    def search_tables(
        self,
        query: str,
        page_size: int,
        page: int,
    ) -> list[model.Layer0TableListItem]:
        return self.table_repo.search_tables(query, page_size, page)

    def update_column_metadata(self, table_name: str, column_description: model.ColumnDescription) -> None:
        return self.table_repo.update_column_metadata(table_name, column_description)

    def register_records(self, table_name: str, record_ids: list[str]) -> None:
        return self.records_repo.register_records(table_name, record_ids)

    def get_table_statistics(self, table_name: str) -> model.TableStatistics:
        return self.records_repo.get_table_statistics(table_name)

    def get_processed_records(
        self,
        limit: int,
        offset: str | None = None,
        row_offset: int | None = None,
        table_name: str | None = None,
        status: Sequence[enums.RecordCrossmatchStatus] | None = None,
        triage_status: Sequence[enums.RecordTriageStatus] | None = None,
        record_id: str | None = None,
    ) -> list[model.CrossmatchRecordRow]:
        return self.records_repo.get_processed_records(
            limit, offset, row_offset, table_name, status, triage_status, record_id
        )

    def set_crossmatch_results(self, rows: list[tuple[str, enums.RecordTriageStatus, list[int]]]) -> None:
        return self.records_repo.set_crossmatch_results(rows)

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        return self.records_repo.upsert_pgc(pgcs)
