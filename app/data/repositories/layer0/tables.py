import datetime
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas
import structlog
from astropy import table
from astropy import units as u
from psycopg import sql

from app.data import model, repositories, template
from app.data.repositories.layer0.common import INTERNAL_ID_COLUMN_NAME, RAWDATA_SCHEMA
from app.lib.storage import postgres
from app.lib.web.errors import DatabaseError

log: structlog.stdlib.BoundLogger = structlog.get_logger()


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

    def create_table(self, data: model.Layer0TableMeta) -> model.Layer0CreationResponse:
        """
        Creates table, writes metadata and returns integer that identifies the table for
        further requests. If table already exists, returns its ID instead of creating a new one.
        """
        table_id, ok = self._get_table_id(data.table_name)
        if ok:
            return model.Layer0CreationResponse(table_id, False)

        fields = []

        for column_descr in data.column_descriptions:
            constraint = ""
            if column_descr.is_primary_key:
                constraint = "PRIMARY KEY"

            fields.append((column_descr.name, column_descr.data_type, constraint))

        with self.with_tx():
            row = self._storage.query_one(
                template.INSERT_TABLE_REGISTRY_ITEM,
                params=[data.bibliography_id, data.table_name, data.datatype],
            )
            table_id = int(row.get("id"))

            self._storage.exec(
                template.build_create_table_query(
                    schema=RAWDATA_SCHEMA,
                    name=data.table_name,
                    fields=fields,
                )
            )

            if data.description is not None:
                self._storage.exec(
                    "SELECT meta.setparams(%s, %s, %s::json)",
                    params=[RAWDATA_SCHEMA, data.table_name, json.dumps({"description": data.description})],
                )

            for column_descr in data.column_descriptions:
                self.update_column_metadata(data.table_name, column_descr)

        return model.Layer0CreationResponse(table_id, True)

    def insert_raw_data(self, data: model.Layer0RawData) -> None:
        if len(data.data) == 0:
            log.warn("trying to insert 0 rows into the table", table_name=data.table_name)
            return

        fields = list(data.data.columns)
        field_identifiers = sql.SQL(",").join([sql.Identifier(f) for f in fields])
        placeholders = sql.SQL(",").join([sql.Placeholder()] * len(fields))
        query = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({}) ON CONFLICT DO NOTHING").format(
            sql.Identifier(RAWDATA_SCHEMA),
            sql.Identifier(data.table_name),
            field_identifiers,
            placeholders,
        )
        query_str = self._storage.query_str(query)

        rows: list[list[Any]] = []
        for row in data.data.to_dict(orient="records"):
            row_values = []
            for field in fields:
                value = row[field]
                if type(value) in (int, float) and np.isnan(value):
                    value = None
                row_values.append(value)
            rows.append(row_values)

        self._storage.execute_batch(query_str, rows)

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
        :param table_id: ID of the raw table
        :param columns: select only given columns
        :param order_column: orders result by a provided column
        :param order_direction: if `order_column` is specified, sets order direction. Either `asc` or `desc`.
        :param offset: allows to retrieve rows starting from the `offset` record_id
        :param limit: allows to retrieve no more than `limit` rows
        """

        meta = self.fetch_metadata_by_name(table_name)

        if columns:
            columns_sql = sql.SQL(",").join([sql.Identifier(c) for c in columns])
        else:
            columns_sql = sql.SQL("*")

        params = []
        parts: list[sql.Composable] = [
            sql.SQL("SELECT {} FROM {}.{}").format(
                columns_sql,
                sql.Identifier(RAWDATA_SCHEMA),
                sql.Identifier(table_name),
            )
        ]

        if offset is not None:
            parts.append(
                sql.SQL(" WHERE {} > %s").format(
                    sql.Identifier(repositories.INTERNAL_ID_COLUMN_NAME),
                )
            )
            params.append(offset)

        if order_column is not None:
            if order_direction not in ("asc", "desc"):
                raise ValueError(f"invalid order direction: {order_direction}")
            parts.append(sql.SQL(" ORDER BY {} ").format(sql.Identifier(order_column)))
            parts.append(sql.SQL(order_direction))

        if limit is not None:
            parts.append(sql.SQL(" LIMIT %s"))
            params.append(limit)

        rows = self._storage.query(sql.Composed(parts), params=params)
        df = pandas.DataFrame(rows)
        tbl = table.Table()
        if len(df) == 0:
            return tbl

        for col in meta.column_descriptions:
            values = df[col.name]

            if col.unit is not None:
                try:
                    if isinstance(col.unit, u.LogUnit):
                        values = u.Quantity(col.unit.to_physical(values), col.unit.physical_unit)
                    else:
                        values = u.Quantity(values, col.unit)
                except Exception as e:
                    log.warning("Unable to assign unit to column", error=e, column=col.name, unit=col.unit)
                    values = QuantityMock(values, col.unit)

            tbl[col.name] = values

        return tbl

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
        """
        :param table_name: Name of the raw table
        :param columns: select only given columns
        :param order_column: orders result by a provided column
        :param order_direction: if `order_column` is specified, sets order direction. Either `asc` or `desc`.
        :param offset: allows to retrieve rows starting from the `offset` record_id.
        :param record_id: retrieves only the row with the given record_id. Other filters are still applied.
        :param limit: allows to retrieve no more than `limit` rows.
        :param row_offset: skip this many rows (use with limit for page-based pagination).
        :return: Layer0RawData
        """

        if table_name is None and record_id is not None:
            table_name = self._resolve_table_name(record_id)

        if table_name is None:
            raise ValueError("either table_name or record_id must be provided")

        if columns:
            columns_sql = sql.SQL(",").join([sql.Identifier(c) for c in columns])
        else:
            columns_sql = sql.SQL("*")

        params = []
        where_parts: list[sql.Composable] = []

        if offset is not None:
            where_parts.append(
                sql.SQL("{} > %s").format(
                    sql.Identifier(repositories.INTERNAL_ID_COLUMN_NAME),
                )
            )
            params.append(offset)

        if record_id is not None:
            where_parts.append(
                sql.SQL("{} = %s").format(
                    sql.Identifier(INTERNAL_ID_COLUMN_NAME),
                )
            )
            params.append(record_id)

        parts: list[sql.Composable] = [
            sql.SQL("SELECT {} FROM {}.{}").format(
                columns_sql,
                sql.Identifier(RAWDATA_SCHEMA),
                sql.Identifier(table_name),
            )
        ]

        if where_parts:
            parts.append(sql.SQL(" WHERE "))
            parts.append(sql.SQL(" AND ").join(where_parts))

        if order_column is not None:
            if order_direction not in ("asc", "desc"):
                raise ValueError(f"invalid order direction: {order_direction}")
            parts.append(sql.SQL(" ORDER BY {} ").format(sql.Identifier(order_column)))
            parts.append(sql.SQL(order_direction))
        elif row_offset is not None:
            parts.append(
                sql.SQL(" ORDER BY {} ").format(
                    sql.Identifier(repositories.INTERNAL_ID_COLUMN_NAME),
                )
            )

        if limit is not None:
            parts.append(sql.SQL(" LIMIT %s"))
            params.append(limit)

        if row_offset is not None:
            parts.append(sql.SQL(" OFFSET %s"))
            params.append(row_offset)

        rows = self._storage.query(sql.Composed(parts), params=params)
        return model.Layer0RawData(table_name, pandas.DataFrame(rows))

    def fetch_records(
        self,
        table_name: str,
        limit: int,
        row_offset: int,
        order_direction: str = "asc",
        has_pgc: bool | None = None,
        pgc_value: int | None = None,
    ) -> list[model.TableRecord]:
        where_parts: list[str] = []
        if has_pgc is True:
            where_parts.append("o.pgc IS NOT NULL")
        elif has_pgc is False:
            where_parts.append("o.pgc IS NULL")
        if pgc_value is not None:
            where_parts.append("o.pgc = %s")

        params: list[Any] = []
        if pgc_value is not None:
            params.append(pgc_value)
        params.append(limit)
        params.append(row_offset)

        id_col = sql.Identifier(INTERNAL_ID_COLUMN_NAME)
        parts: list[sql.Composable] = [
            sql.SQL("SELECT r.*, o.pgc FROM {}.{} AS r JOIN layer0.records AS o ON r.{} = o.id").format(
                sql.Identifier(RAWDATA_SCHEMA),
                sql.Identifier(table_name),
                id_col,
            ),
        ]
        if where_parts:
            parts.append(sql.SQL(" WHERE "))
            parts.append(sql.SQL(" AND ").join([sql.SQL(w) for w in where_parts]))
        parts.append(sql.SQL(" ORDER BY r.{} ").format(id_col))
        parts.append(sql.SQL(order_direction if order_direction in ("asc", "desc") else "asc"))
        parts.append(sql.SQL(" LIMIT %s OFFSET %s"))

        rows = self._storage.query(sql.Composed(parts), params=params)
        id_col_name = INTERNAL_ID_COLUMN_NAME
        drop_labels = [id_col_name, "pgc"]
        result: list[model.TableRecord] = []
        for row in rows:
            record_id = str(row[id_col_name])
            original_data = _row_to_serializable_dict(row, drop=drop_labels)
            pgc_val = row.get("pgc")
            if pgc_val is not None and (pandas.isna(pgc_val) or (isinstance(pgc_val, float) and np.isnan(pgc_val))):
                pgc_val = None
            result.append(
                model.TableRecord(
                    id=record_id,
                    original_data=original_data,
                    pgc=int(pgc_val) if pgc_val is not None else None,
                )
            )
        return result

    def _resolve_table_name(self, record_id: str) -> str | None:
        rows = self._storage.query(
            """
            SELECT t.table_name
            FROM layer0.records AS o
            JOIN layer0.tables AS t ON o.table_id = t.id
            WHERE o.id = %s
            """,
            params=[record_id],
        )
        return rows[0]["table_name"] if rows else None

    def fetch_metadata(self, table_name: str) -> model.Layer0TableMeta:
        return self.fetch_metadata_by_name(table_name)

    def fetch_metadata_by_name(self, table_name: str) -> model.Layer0TableMeta:
        row = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])
        if row is None:
            raise DatabaseError(f"unable to fetch table with name {table_name}")

        modification_dt: datetime.datetime | None = row.get("modification_dt")
        return self._fetch_metadata_by_name(table_name, modification_dt)

    def _fetch_metadata_by_name(
        self, table_name: str, modification_dt: datetime.datetime | None
    ) -> model.Layer0TableMeta:
        column_descriptions = self._storage.query(
            "SELECT column_name, param FROM meta.column_info WHERE schema_name=%s AND table_name=%s",
            params=[RAWDATA_SCHEMA, table_name],
        )

        descriptions = []
        for description in column_descriptions:
            column_name = description["column_name"]
            metadata = description["param"]

            unit = None
            if metadata.get("unit") is not None:
                unit = u.Unit(metadata["unit"])

            descriptions.append(
                model.ColumnDescription(
                    column_name,
                    metadata["data_type"],
                    unit=unit,
                    description=metadata["description"],
                    ucd=metadata.get("ucd"),
                )
            )

        table_metadata = self._storage.query_one(template.FETCH_TABLE_METADATA, params=[RAWDATA_SCHEMA, table_name])
        registry_item = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])

        if table_metadata is None:
            raise DatabaseError(f"unable to metadata for table {table_name}")

        return model.Layer0TableMeta(
            table_name,
            descriptions,
            registry_item["bib"],
            registry_item["datatype"],
            modification_dt,
            table_metadata["param"].get("description"),
            table_id=registry_item["id"],
        )

    def update_column_metadata(self, table_name: str, column_description: model.ColumnDescription) -> None:
        table_id, _ = self._get_table_id(table_name)

        column_params = {
            "description": column_description.description,
            "data_type": column_description.data_type,
        }

        if column_description.unit is not None:
            column_params["unit"] = column_description.unit.to_string()

        if column_description.ucd is not None:
            column_params["ucd"] = column_description.ucd

        modification_query = "UPDATE layer0.tables SET modification_dt = now() WHERE id = %s"

        self._storage.exec(
            "SELECT meta.setparams(%s, %s, %s, %s::json)",
            params=[RAWDATA_SCHEMA, table_name, column_description.name, json.dumps(column_params)],
        )
        self._storage.exec(modification_query, params=[table_id])

    def search_tables(
        self,
        query: str,
        page_size: int,
        page: int,
    ) -> list[model.Layer0TableListItem]:
        pattern = f"%{query}%" if query else "%"
        offset = page * page_size

        sql = """
        SELECT
            t.table_name,
            t.modification_dt,
            COALESCE(ti.param->>'description', '') AS description,
            COALESCE(ps.n_live_tup::bigint, 0)::int AS num_entries,
            (
                SELECT COUNT(*)::int
                FROM meta.column_info c
                WHERE c.schema_name = %s
                  AND c.table_name = t.table_name
                  AND c.column_name != %s
            ) AS num_fields
        FROM layer0.tables t
        LEFT JOIN meta.table_info ti
            ON ti.schema_name = %s AND ti.table_name = t.table_name
        LEFT JOIN pg_stat_user_tables ps
            ON ps.schemaname = %s AND ps.relname = t.table_name
        WHERE t.table_name ILIKE %s OR COALESCE(ti.param->>'description', '') ILIKE %s
        ORDER BY t.modification_dt DESC
        LIMIT %s OFFSET %s
        """
        params = [
            RAWDATA_SCHEMA,
            INTERNAL_ID_COLUMN_NAME,
            RAWDATA_SCHEMA,
            RAWDATA_SCHEMA,
            pattern,
            pattern,
            page_size,
            offset,
        ]
        rows = self._storage.query(sql, params=params)
        return [
            model.Layer0TableListItem(
                table_name=row["table_name"],
                description=row["description"] or "",
                num_entries=int(row["num_entries"]),
                num_fields=int(row["num_fields"]),
                modification_dt=row["modification_dt"],
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
