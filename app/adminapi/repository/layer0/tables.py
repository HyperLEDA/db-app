import datetime
import json
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas
import psycopg
import structlog
from astropy import table
from astropy import units as u
from psycopg import sql

from app.adminapi import model
from app.adminapi.repository import sql as repo_sql
from app.adminapi.repository.layer0 import common as layer0_common
from app.adminapi.repository.layer0.common import INTERNAL_ID_COLUMN_NAME, RAWDATA_SCHEMA, metadata_to_candidates
from app.catalogs.layer0 import build_raw_table_select
from app.lib.storage import enums, postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()


_INTEGER_TYPE_NAMES = {"int2", "int4", "int8"}


def _copy_column(series: pandas.Series, pg_type_name: str) -> list[Any]:
    if pg_type_name in _INTEGER_TYPE_NAMES:
        # pandas stores integer columns that contain nulls as floats, which binary COPY would reject.
        series = series.astype("Int64")

    values = series.astype(object).to_numpy(copy=True)
    values[series.isna().to_numpy()] = None
    return values.tolist()


def _statistics_from_json(raw: Any) -> model.TableProgress | None:
    if raw is None:
        return None
    if isinstance(raw, memoryview):
        raw = raw.tobytes().decode()
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode()
    if isinstance(raw, str):
        raw = json.loads(raw)
    catalogs = raw["catalogs"]
    columns = {
        name: model.ColumnProgress(
            non_null_count=int(column["non_null_count"]),
            min=column.get("min"),
            max=column.get("max"),
        )
        for name, column in raw.get("columns", {}).items()
    }
    return model.TableProgress(
        total_records=int(raw["total_records"]),
        unprocessed=int(raw["unprocessed"]),
        pending_triage=int(raw["pending_triage"]),
        resolved_unsubmitted=int(raw["resolved_unsubmitted"]),
        submitted=int(raw["submitted"]),
        catalogs={
            name: model.CatalogProgress(structured=int(catalog["structured"])) for name, catalog in catalogs.items()
        },
        columns=columns,
    )


def _row_to_serializable_dict(row: Any, drop: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in row.items():
        if k in drop:
            continue
        if v is None or (isinstance(v, float) and np.isnan(v)):
            out[k] = None
        elif isinstance(v, (datetime.datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@dataclass
class QuantityMock:
    values: pandas.Series
    unit: u.Unit

    def __getitem__(self, key):
        return self.values[key]


class Layer0TableRepository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage) -> None:
        super().__init__(storage)

    @contextmanager
    def rawdata_table(self, table_name: str) -> Generator[int]:
        with layer0_common.rawdata_table(self._storage, table_name=table_name) as table_ids:
            yield table_ids[0]

    def get_table_metadata(self, schema: str, table: str) -> postgres.TableInfo:
        return postgres.get_table_metadata(self._storage, schema, table)

    def create_table(self, data: model.Layer0TableMeta) -> model.Layer0CreationResponse:
        """
        Creates table, writes metadata and returns integer that identifies the table for
        further requests. If table already exists, returns its ID instead of creating a new one.
        """
        table_id, ok = self._get_table_id(data.table_info.name)
        if ok:
            return model.Layer0CreationResponse(table_id, False)

        fields = []

        for column in data.table_info.columns.values():
            constraint = ""
            if column.name in data.table_info.primary_keys:
                constraint = "PRIMARY KEY"

            fields.append((column.name, column.data_type, constraint))

        with self.with_tx():
            row = self._storage.query_one(
                repo_sql.INSERT_TABLE_REGISTRY_ITEM,
                params=[data.bibliography_id, data.table_info.name, data.datatype, data.note],
            )
            table_id = int(row.get("id"))

            self._storage.exec(
                repo_sql.build_create_table_query(
                    schema=RAWDATA_SCHEMA,
                    name=data.table_info.name,
                    fields=fields,
                )
            )

            with self.rawdata_table(data.table_info.name):
                if data.table_info.description is not None:
                    self._storage.exec(
                        "SELECT meta.setparams(%s, %s, %s::json)",
                        params=[
                            RAWDATA_SCHEMA,
                            data.table_info.name,
                            json.dumps({"description": data.table_info.description}),
                        ],
                    )

                for column in data.table_info.columns.values():
                    self._set_column_metadata(data.table_info.name, column)

        return model.Layer0CreationResponse(table_id, True)

    def insert_raw_data(self, data: model.Layer0RawData) -> None:
        if len(data.data) == 0:
            log.warn("trying to insert 0 rows into the table", table_name=data.table_name)
            return

        fields = list(data.data.columns)
        field_identifiers = sql.SQL(",").join([sql.Identifier(f) for f in fields])
        table_ident = sql.SQL("{}.{}").format(
            sql.Identifier(RAWDATA_SCHEMA),
            sql.Identifier(data.table_name),
        )

        with self.rawdata_table(data.table_name):
            with self._storage.get_connection().cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE TEMP TABLE raw_staging (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
                        table_ident
                    )
                )
                type_rows = self._storage.query(
                    "SELECT a.attname, a.atttypid, t.typname FROM pg_attribute a "
                    "JOIN pg_type t ON t.oid = a.atttypid "
                    "WHERE a.attrelid = 'raw_staging'::regclass AND a.attnum > 0 AND NOT a.attisdropped"
                )
                column_types = {row["attname"]: (row["atttypid"], row["typname"]) for row in type_rows}

                for field in fields:
                    if field not in column_types:
                        raise psycopg.errors.UndefinedColumn(
                            f'column "{field}" of relation "{data.table_name}" does not exist'
                        )

                columns = [_copy_column(data.data[field], column_types[field][1]) for field in fields]
                with cur.copy(
                    sql.SQL("COPY raw_staging ({}) FROM STDIN (FORMAT BINARY)").format(field_identifiers)
                ) as copy:
                    copy.set_types([column_types[field][0] for field in fields])
                    for row in zip(*columns, strict=True):
                        copy.write_row(row)
                cur.execute(
                    sql.SQL("INSERT INTO {} ({}) SELECT {} FROM raw_staging ON CONFLICT DO NOTHING").format(
                        table_ident,
                        field_identifiers,
                        field_identifiers,
                    )
                )

    def fetch_table(
        self,
        table_name: str,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
    ) -> table.Table:
        """
        :param table_name: Name of the raw table
        :param columns: select only given columns
        :param order_column: orders result by a provided column
        :param order_direction: if `order_column` is specified, sets order direction. Either `asc` or `desc`.
        :param offset: allows to retrieve rows starting from the `offset` record_id
        :param limit: allows to retrieve no more than `limit` rows
        """

        meta = self.fetch_metadata_by_name(table_name)
        query, params = build_raw_table_select(
            table_name,
            columns=columns,
            offset=offset,
            order_column=order_column,
            order_direction=order_direction,
            limit=limit,
        )
        rows = self._storage.query(query, params=params)
        df = pandas.DataFrame(rows)
        tbl = table.Table()
        if len(df) == 0:
            return tbl

        for col in meta.table_info.columns.values():
            values = df[col.name]

            if col.unit is not None:
                unit = u.Unit(col.unit)
                try:
                    if isinstance(unit, u.LogUnit):
                        values = u.Quantity(unit.to_physical(values), unit.physical_unit)
                    else:
                        values = u.Quantity(values, unit)
                except Exception as e:
                    log.warning("Unable to assign unit to column", error=e, column=col.name, unit=unit)
                    values = QuantityMock(values, unit)

            tbl[col.name] = values

        return tbl

    def fetch_raw_data(
        self,
        table_name: str,
        offset: str | None = None,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        limit: int | None = None,
        row_offset: int | None = None,
    ) -> model.Layer0RawData:
        """
        :param table_name: Name of the raw table
        :param columns: select only given columns
        :param order_column: orders result by a provided column
        :param order_direction: if `order_column` is specified, sets order direction. Either `asc` or `desc`.
        :param offset: allows to retrieve rows starting from the `offset` record_id.
        :param limit: allows to retrieve no more than `limit` rows.
        :param row_offset: skip this many rows (use with limit for page-based pagination).
        :return: Layer0RawData
        """

        query, params = build_raw_table_select(
            table_name,
            columns=columns,
            offset=offset,
            order_column=order_column,
            order_direction=order_direction,
            limit=limit,
            row_offset=row_offset,
        )
        rows = self._storage.query(query, params=params)
        return model.Layer0RawData(table_name, pandas.DataFrame(rows))

    def fetch_records(
        self,
        table_name: str | None,
        limit: int,
        row_offset: int,
        order_direction: str = "asc",
        has_pgc: bool | None = None,
        pgc_value: int | None = None,
        triage_status: str | None = None,
        record_id: str | None = None,
    ) -> list[model.TableRecord]:
        where_parts: list[str] = []
        params: list[Any] = []

        if table_name is not None:
            where_parts.append("t.table_name = %s")
            params.append(table_name)
        if has_pgc is True:
            where_parts.append("o.pgc IS NOT NULL")
        elif has_pgc is False:
            where_parts.append("o.pgc IS NULL")
        if pgc_value is not None:
            where_parts.append("o.pgc = %s")
            params.append(pgc_value)
        if record_id is not None:
            where_parts.append("o.id = %s")
            params.append(record_id)

        direction = sql.SQL(order_direction if order_direction in ("asc", "desc") else "asc")

        if triage_status == "unprocessed":
            where_parts.append("NOT EXISTS (SELECT 1 FROM layer0.crossmatch c WHERE c.record_id = o.id)")
            select_sql = (
                "SELECT o.id, o.pgc, t.table_name FROM layer0.records AS o JOIN layer0.tables AS t ON o.table_id = t.id"
            )
        elif triage_status in ("pending", "resolved"):
            where_parts.append("c.triage_status = %s")
            params.append(triage_status)
            select_sql = (
                "SELECT o.id, o.pgc, t.table_name, c.triage_status, c.metadata AS crossmatch_metadata "
                "FROM layer0.records AS o "
                "JOIN layer0.tables AS t ON o.table_id = t.id "
                "JOIN layer0.crossmatch AS c ON o.id = c.record_id"
            )
        else:
            select_sql = (
                "SELECT o.id, o.pgc, t.table_name, c.triage_status, c.metadata AS crossmatch_metadata "
                "FROM layer0.records AS o "
                "JOIN layer0.tables AS t ON o.table_id = t.id "
                "LEFT JOIN layer0.crossmatch AS c ON o.id = c.record_id"
            )

        parts: list[sql.Composable] = [sql.SQL(select_sql)]
        if where_parts:
            parts.append(sql.SQL(" WHERE "))
            parts.append(sql.SQL(" AND ").join(sql.SQL(part) for part in where_parts))
        parts.append(sql.SQL(" ORDER BY o.id "))
        parts.append(direction)
        parts.append(sql.SQL(" LIMIT %s OFFSET %s"))
        params.append(limit)
        params.append(row_offset)

        rows = self._storage.query(sql.Composed(parts), params=params)
        original_by_id = self._fetch_original_data(rows)
        result: list[model.TableRecord] = []
        for row in rows:
            record_id = str(row["id"])
            pgc_val = row.get("pgc")
            if pgc_val is not None and (pandas.isna(pgc_val) or (isinstance(pgc_val, float) and np.isnan(pgc_val))):
                pgc_val = None
            raw_triage = row.get("triage_status")
            triage_val = raw_triage if raw_triage is not None else "unprocessed"
            candidates = metadata_to_candidates(row.get("crossmatch_metadata"))
            result.append(
                model.TableRecord(
                    id=record_id,
                    original_data=original_by_id.get(record_id, {}),
                    pgc=int(pgc_val) if pgc_val is not None else None,
                    triage_status=triage_val,
                    crossmatch_candidates=candidates,
                    table_name=str(row["table_name"]),
                )
            )
        return result

    def _fetch_original_data(self, rows: Sequence[Any]) -> dict[str, dict[str, Any]]:
        ids_by_table: dict[str, list[str]] = {}
        for row in rows:
            ids_by_table.setdefault(str(row["table_name"]), []).append(str(row["id"]))

        original_by_id: dict[str, dict[str, Any]] = {}
        id_col = INTERNAL_ID_COLUMN_NAME
        for raw_table_name, record_ids in ids_by_table.items():
            query = sql.SQL("SELECT * FROM {}.{} WHERE {} = ANY(%s)").format(
                sql.Identifier(RAWDATA_SCHEMA),
                sql.Identifier(raw_table_name),
                sql.Identifier(id_col),
            )
            try:
                raw_rows = self._storage.query(query, params=[record_ids])
            except Exception as exc:
                log.error("Failed to load original data", table_name=raw_table_name, exc_info=exc)
                continue
            for raw in raw_rows:
                original_by_id[str(raw[id_col])] = _row_to_serializable_dict(raw, drop=[id_col])
        return original_by_id

    def fetch_metadata(self, table_name: str) -> model.Layer0TableMeta:
        return self.fetch_metadata_by_name(table_name)

    def fetch_metadata_by_name(self, table_name: str) -> model.Layer0TableMeta:
        table_info = self.get_table_metadata(RAWDATA_SCHEMA, table_name)
        registry_item = self._storage.query_one(repo_sql.FETCH_RAWDATA_REGISTRY, params=[table_name])

        return model.Layer0TableMeta(
            table_info=table_info,
            bibliography_id=registry_item["bib"],
            datatype=registry_item["datatype"],
            status=registry_item["status"],
            modification_dt=registry_item.get("modification_dt"),
            table_id=registry_item["id"],
            statistics=_statistics_from_json(registry_item.get("statistics")),
            note=registry_item.get("note"),
        )

    def _set_column_metadata(self, table_name: str, column: postgres.ColumnInfo) -> None:
        column_params: dict[str, str | None] = {
            "description": column.description,
        }

        if column.unit is not None:
            column_params["unit"] = column.unit

        if column.ucd is not None:
            column_params["ucd"] = column.ucd

        self._storage.exec(
            "SELECT meta.setparams(%s, %s, %s, %s::json)",
            params=[RAWDATA_SCHEMA, table_name, column.name, json.dumps(column_params)],
        )

    def update_column_metadata(self, table_name: str, column: postgres.ColumnInfo) -> None:
        with self.rawdata_table(table_name):
            self._set_column_metadata(table_name, column)

    def update_table_metadata(self, table_name: str, description: str) -> None:
        with self.rawdata_table(table_name):
            self._storage.exec(
                "SELECT meta.setparams(%s, %s, %s::json)",
                params=[RAWDATA_SCHEMA, table_name, json.dumps({"description": description})],
            )

    def update_table_note(self, table_name: str, note: str | None) -> None:
        with self.rawdata_table(table_name) as table_id:
            self._storage.exec(
                "UPDATE layer0.tables SET note = %s WHERE id = %s",
                params=[note, table_id],
            )

    def update_table_datatype(self, table_name: str, datatype: enums.DataType) -> None:
        with self.rawdata_table(table_name) as table_id:
            self._storage.exec(
                "UPDATE layer0.tables SET datatype = %s WHERE id = %s",
                params=[datatype, table_id],
            )

    def update_table_status(self, table_name: str, status: enums.TableStatus) -> None:
        with self.rawdata_table(table_name) as table_id:
            self._storage.exec(
                "UPDATE layer0.tables SET status = %s WHERE id = %s",
                params=[status, table_id],
            )

    def is_raw_table_name_taken(self, table_name: str) -> bool:
        return self._get_table_id(table_name)[1]

    def rename_raw_table(self, old_table_name: str, new_table_name: str) -> None:
        with self.rawdata_table(old_table_name) as table_id:
            rename_q = sql.SQL("ALTER TABLE {}.{} RENAME TO {}").format(
                sql.Identifier(RAWDATA_SCHEMA),
                sql.Identifier(old_table_name),
                sql.Identifier(new_table_name),
            )
            self._storage.exec(rename_q)
            self._storage.exec(
                "UPDATE layer0.tables SET table_name = %s WHERE id = %s",
                params=[new_table_name, table_id],
            )

    def search_tables(
        self,
        query: str,
        page_size: int,
        page: int,
        statuses: list[enums.TableStatus],
    ) -> list[model.Layer0TableListItem]:
        pattern = f"%{query}%" if query else "%"
        offset = page * page_size

        sql_query = """
        SELECT
            t.table_name,
            t.status,
            t.modification_dt,
            t.statistics,
            t.note,
            COALESCE(ti.param->>'description', '') AS description,
            b.code AS bibcode,
            (
                SELECT COUNT(*)::int
                FROM meta.column_info c
                WHERE c.schema_name = %s
                  AND c.table_name = t.table_name
                  AND c.column_name != %s
            ) AS num_fields
        FROM layer0.tables t
        JOIN common.bib b ON b.id = t.bib
        LEFT JOIN meta.table_info ti
            ON ti.schema_name = %s AND ti.table_name = t.table_name
        WHERE (t.table_name ILIKE %s OR COALESCE(ti.param->>'description', '') ILIKE %s)
          AND t.status = ANY(%s)
        ORDER BY t.modification_dt DESC
        LIMIT %s OFFSET %s
        """
        params = [
            RAWDATA_SCHEMA,
            INTERNAL_ID_COLUMN_NAME,
            RAWDATA_SCHEMA,
            pattern,
            pattern,
            statuses,
            page_size,
            offset,
        ]
        rows = self._storage.query(sql_query, params=params)
        return [
            model.Layer0TableListItem(
                table_name=row["table_name"],
                description=row["description"] or "",
                num_fields=int(row["num_fields"]),
                modification_dt=row["modification_dt"],
                bibcode=row["bibcode"],
                status=row["status"],
                statistics=_statistics_from_json(row.get("statistics")),
                note=row.get("note"),
            )
            for row in rows
        ]

    def _get_table_id(self, table_name: str) -> tuple[int, bool]:
        try:
            row = self._storage.query_one(
                "SELECT id FROM layer0.tables WHERE table_name = %s",
                params=[table_name],
            )
        except RuntimeError:
            return 0, False

        return row["id"], True
