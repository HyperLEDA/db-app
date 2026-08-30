from collections.abc import Sequence
from typing import Any, final

import structlog
from astropy import table

from app import catalogs
from app.adminapi import model
from app.adminapi.repository import common, layer1, layer2, metadata
from app.adminapi.repository import model as repo_model
from app.adminapi.repository.layer0 import records, tables
from app.lib.storage import enums, postgres


@final
class Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

        self._common = common.CommonRepository(storage, logger)
        self._layer0_tables = tables.Layer0TableRepository(storage)
        self._layer0_records = records.Layer0RecordRepository(storage)
        self._layer1 = layer1.Layer1Repository(storage, logger)
        self._layer2 = layer2.Layer2Repository(storage, logger)
        self._metadata = metadata.MetadataRepository(storage)

    def create_bibliography(self, code: str, year: int, authors: list[str], title: str) -> int:
        return self._common.create_bibliography(code, year, authors, title)

    def get_source_entry(self, source_name: str) -> model.Bibliography:
        return self._common.get_source_entry(source_name)

    def get_source_by_id(self, source_id: int) -> model.Bibliography:
        return self._common.get_source_by_id(source_id)

    def register_pgcs(self, pgcs: list[int]) -> None:
        return self._common.register_pgcs(pgcs)

    def get_existing_pgcs(self, pgcs: list[int]) -> set[int]:
        return self._common.get_existing_pgcs(pgcs)

    def get_table_metadata(self, schema_name: str, table_name: str) -> postgres.TableInfo:
        return self._common.get_table_metadata(schema_name, table_name)

    def get_nature_object_types(self) -> list[dict]:
        return self._common.get_nature_object_types()

    def create_table(self, data: model.Layer0TableMeta) -> model.Layer0CreationResponse:
        return self._layer0_tables.create_table(data)

    def insert_raw_data(self, data: model.Layer0RawData) -> None:
        return self._layer0_tables.insert_raw_data(data)

    def fetch_table(
        self,
        table_name: str,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
    ) -> table.Table:
        return self._layer0_tables.fetch_table(table_name, offset, columns, order_column, order_direction, limit)

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
        return self._layer0_tables.fetch_raw_data(
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
        return self._layer0_tables.fetch_records(
            table_name, limit, row_offset, order_direction, has_pgc, pgc_value, triage_status
        )

    def fetch_metadata(self, table_name: str) -> model.Layer0TableMeta:
        return self._layer0_tables.fetch_metadata(table_name)

    def fetch_metadata_by_name(self, table_name: str) -> model.Layer0TableMeta:
        return self._layer0_tables.fetch_metadata_by_name(table_name)

    def search_tables(
        self,
        query: str,
        page_size: int,
        page: int,
        statuses: list[enums.TableStatus],
    ) -> list[model.Layer0TableListItem]:
        return self._layer0_tables.search_tables(query, page_size, page, statuses)

    def update_column_metadata(self, table_name: str, column: postgres.ColumnInfo) -> None:
        return self._layer0_tables.update_column_metadata(table_name, column)

    def update_table_metadata(self, table_name: str, description: str) -> None:
        return self._layer0_tables.update_table_metadata(table_name, description)

    def update_table_datatype(self, table_name: str, datatype: enums.DataType) -> None:
        return self._layer0_tables.update_table_datatype(table_name, datatype)

    def update_table_status(self, table_name: str, status: enums.TableStatus) -> None:
        return self._layer0_tables.update_table_status(table_name, status)

    def is_raw_table_name_taken(self, table_name: str) -> bool:
        return self._layer0_tables.is_raw_table_name_taken(table_name)

    def rename_raw_table(self, old_table_name: str, new_table_name: str) -> None:
        return self._layer0_tables.rename_raw_table(old_table_name, new_table_name)

    def register_records(self, table_name: str, record_ids: list[str]) -> None:
        return self._layer0_records.register_records(table_name, record_ids)

    def get_table_progress(self, table_names: list[str] | None = None) -> dict[str, model.TableProgress]:
        return self._layer0_records.get_table_progress(table_names)

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
        return self._layer0_records.get_processed_records(
            limit, offset, row_offset, table_name, status, triage_status, record_id
        )

    def set_crossmatch_results(self, rows: list[tuple[str, enums.RecordTriageStatus, list[int]]]) -> None:
        return self._layer0_records.set_crossmatch_results(rows)

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        return self._layer0_records.upsert_pgc(pgcs)

    def assign_record_pgcs(self, record_ids: list[str]) -> None:
        return self._layer0_records.assign_record_pgcs(record_ids)

    def merge_pgcs(self, target_pgc: int, source_pgcs: list[int]) -> int:
        return self._layer0_records.merge_pgcs(target_pgc, source_pgcs)

    def get_column_units(self, catalog: catalogs.RawCatalog) -> dict[str, str]:
        return self._layer1.get_column_units(catalog)

    def save_structured_data(
        self,
        table: str,
        columns: list[str],
        ids: list[str],
        data: list[list[Any]],
        conflict_keys: list[str] | None = None,
    ) -> None:
        return self._layer1.save_structured_data(table, columns, ids, data, conflict_keys)

    def get_designation_records(self, record_ids: list[str]) -> list[model.DesignationRecord | None]:
        return self._layer1.get_designation_records(record_ids)

    def get_icrs_records(self, record_ids: list[str]) -> list[model.ICRSRecord | None]:
        return self._layer1.get_icrs_records(record_ids)

    def get_redshift_records(self, record_ids: list[str]) -> list[model.RedshiftRecord | None]:
        return self._layer1.get_redshift_records(record_ids)

    def get_nature_records(self, record_ids: list[str]) -> list[model.NatureRecord | None]:
        return self._layer1.get_nature_records(record_ids)

    def query_records(
        self,
        raw_catalogs: list[catalogs.RawCatalog],
        record_ids: list[str] | None = None,
        table_name: str | None = None,
        offset: str | None = None,
        limit: int | None = None,
    ) -> list[model.Record]:
        return self._layer1.query_records(raw_catalogs, record_ids, table_name, offset, limit)

    def query_catalogs_pgc(
        self,
        raw_catalogs: list[catalogs.RawCatalog],
        pgc_numbers: list[int],
        limit: int,
        offset: int = 0,
    ) -> list[catalogs.Layer2CatalogObject]:
        return self._layer2.query_catalogs_pgc(raw_catalogs, pgc_numbers, limit, offset)

    def query_with_metadata(
        self,
        query: str,
        max_rows: int,
        *,
        timeout_seconds: float | None = None,
    ) -> repo_model.QueryWithMetadataResult:
        kwargs: dict[str, float] = {}
        if timeout_seconds is not None:
            kwargs["timeout_seconds"] = timeout_seconds
        return self._metadata.query_with_metadata(query, max_rows, **kwargs)
