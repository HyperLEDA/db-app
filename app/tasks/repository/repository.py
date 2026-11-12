import datetime
import json
from collections.abc import Sequence
from typing import Any, final

import psycopg
import structlog
from astropy import table
from astropy import units as u
from psycopg import sql

from app.catalogs import layer0, layer1, layer2, table_statistics
from app.lib import concurrency
from app.lib.storage import mapping, postgres

_DEFAULT_E_CZ = u.Quantity(100, u.Unit("km/s"))

_MIN_MAX_TYPES = frozenset(
    {
        mapping.TYPE_INTEGER,
        mapping.TYPE_BIGINT,
        mapping.TYPE_DOUBLE_PRECISION,
        mapping.TYPE_TIMESTAMP,
        mapping.TYPE_TEXT,
        mapping.TYPE_BOOLEAN,
    }
)


@final
class Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def get_last_update_time(self, catalog: layer2.Catalog) -> datetime.datetime:
        return self._storage.query_one("SELECT dt FROM layer2.last_update WHERE catalog = %s", params=[catalog.value])[
            "dt"
        ]

    def update_last_update_time(self, dt: datetime.datetime, catalog: layer2.Catalog) -> None:
        self._storage.exec(
            "UPDATE layer2.last_update SET dt = %s WHERE catalog = %s",
            params=[dt, catalog.value],
        )

    def get_orphaned_pgcs(self, raw_catalogs: list[layer2.Catalog]) -> dict[str, list[int]]:
        result: dict[str, list[int]] = {}
        for catalog in raw_catalogs:
            object_cls = layer2.get_catalog_object_type(catalog)
            layer2_table = object_cls.table()
            missing_sources = []
            for source in object_cls.sources():
                layer1_table = layer1.get_catalog_object_type(source).layer1_table()
                missing_sources.append(f"""
                    NOT EXISTS (
                        SELECT 1
                        FROM layer0.records r
                        INNER JOIN {layer1_table} l1 ON l1.record_id = r.id
                        WHERE r.pgc = l2.pgc
                    )
                """)
            query = f"""
                SELECT l2.pgc FROM {layer2_table} l2
                WHERE {" AND ".join(missing_sources)}
            """
            rows_result = self._storage.query(query)
            result[layer2_table] = [int(row["pgc"]) for row in rows_result]
        return result

    def remove_pgcs(self, raw_catalogs: list[layer2.Catalog], pgcs: list[int]) -> None:
        if not pgcs:
            return

        for catalog in raw_catalogs:
            object_cls = layer2.get_catalog_object_type(catalog)
            layer2_table = object_cls.table()
            query = f"DELETE FROM {layer2_table} WHERE pgc = ANY(%s)"
            self._storage.exec(query, params=[pgcs])
            if catalog is layer2.Catalog.REDSHIFT:
                self._storage.exec("DELETE FROM layer2.velocity WHERE pgc = ANY(%s)", params=[pgcs])

    def save(self, table_name: str, data: table.QTable, *, delete_pgcs: list[int] | None = None) -> None:
        if len(data) == 0 and not delete_pgcs:
            return

        schema, relation = table_name.split(".", maxsplit=1)
        table_ident = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(relation))
        prepared: tuple[sql.Composed, sql.Composed, list[int], list[list[Any]]] | None = None
        if len(data) > 0:
            table_info = self.get_table_metadata(schema, relation)
            column_units = {name: col.unit for name, col in table_info.columns.items() if col.unit}
            pk_columns = [name for name in table_info.columns if name in table_info.primary_keys] or ["pgc"]

            work = table.QTable(data, copy=True)
            columns = [name for name in work.colnames if name != "pgc"]
            for col in columns:
                target_unit = column_units.get(col)
                if target_unit is not None and work[col].unit is not None:
                    work[col] = work[col].to(u.Unit(target_unit))

            all_columns = ["pgc", *columns]
            column_idents = sql.SQL(", ").join(sql.Identifier(c) for c in all_columns)
            on_conflict = sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in all_columns
            )
            conflict_target = sql.SQL(", ").join(sql.Identifier(c) for c in pk_columns)
            insert_sql = sql.SQL(
                "INSERT INTO {} ({}) SELECT {} FROM save_staging ON CONFLICT ({}) DO UPDATE SET {}"
            ).format(table_ident, column_idents, column_idents, conflict_target, on_conflict)
            prepared = (
                column_idents,
                insert_sql,
                [int(pgc) for pgc in work["pgc"]],
                [_column_as_list(work[col]) for col in columns],
            )

        with self.with_tx():
            if delete_pgcs:
                self._storage.exec(
                    sql.SQL("DELETE FROM {} WHERE pgc = ANY(%s)").format(table_ident),
                    params=[delete_pgcs],
                )
            if prepared is None:
                return

            column_idents, insert_sql, pgcs, col_values = prepared
            with self._storage.get_connection().cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE TEMP TABLE save_staging (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
                        table_ident
                    )
                )
                with cur.copy(sql.SQL("COPY save_staging ({}) FROM STDIN").format(column_idents)) as copy:
                    for i, pgc in enumerate(pgcs):
                        copy.write_row((pgc, *[vals[i] for vals in col_values]))
                cur.execute(insert_sql)

    def get_new_nature_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records("nature.data", "l1.type_name", dt, limit, offset)
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "type_name": [r["type_name"] for r in rows],
            }
        )

    def get_new_icrs_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records(
            "icrs.data",
            "l1.ra, l1.e_ra, l1.dec, l1.e_dec, t.datatype",
            dt,
            limit,
            offset,
            extra_joins="JOIN layer0.tables AS t ON o.table_id = t.id",
        )
        icrs_table = layer1.get_catalog_object_type(layer1.Catalog.ICRS).layer1_table()
        icrs_schema, icrs_name = icrs_table.split(".", maxsplit=1)
        icrs_info = self.get_table_metadata(icrs_schema, icrs_name)
        units = {name: col.unit for name, col in icrs_info.columns.items() if col.unit}
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "ra": u.Quantity([float(r["ra"]) for r in rows], u.Unit(units["ra"])),
                "e_ra": u.Quantity([float(r["e_ra"]) for r in rows], u.Unit(units["e_ra"])),
                "dec": u.Quantity([float(r["dec"]) for r in rows], u.Unit(units["dec"])),
                "e_dec": u.Quantity([float(r["e_dec"]) for r in rows], u.Unit(units["e_dec"])),
                "datatype": [r["datatype"].value for r in rows],
            }
        )

    def get_new_redshift_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records(
            "cz.data",
            "l1.cz, l1.e_cz, t.datatype",
            dt,
            limit,
            offset,
            extra_joins="JOIN layer0.tables AS t ON o.table_id = t.id",
        )
        redshift_table = layer1.get_catalog_object_type(layer1.Catalog.REDSHIFT).layer1_table()
        redshift_schema, redshift_name = redshift_table.split(".", maxsplit=1)
        redshift_info = self.get_table_metadata(redshift_schema, redshift_name)
        units = {name: col.unit for name, col in redshift_info.columns.items() if col.unit}
        e_cz_unit = u.Unit(units["e_cz"])
        default_e_cz = float(_DEFAULT_E_CZ.to_value(e_cz_unit))
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "cz": u.Quantity([float(r["cz"]) for r in rows], u.Unit(units["cz"])),
                "e_cz": u.Quantity(
                    [float(r["e_cz"]) if r["e_cz"] is not None else default_e_cz for r in rows],
                    e_cz_unit,
                ),
                "datatype": [r["datatype"].value for r in rows],
            }
        )

    def get_new_morphology_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        morphology_table = layer1.get_catalog_object_type(layer1.Catalog.MORPHOLOGY__T).layer1_table()
        rows = self._query_new_pgc_records(
            morphology_table,
            "l1.value AS t, l1.em_value AS em, l1.ep_value AS ep, t.datatype",
            dt,
            limit,
            offset,
            extra_joins="JOIN layer0.tables AS t ON o.table_id = t.id",
        )
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "t": [float(r["t"]) for r in rows],
                "em": [None if r["em"] is None else float(r["em"]) for r in rows],
                "ep": [None if r["ep"] is None else float(r["ep"]) for r in rows],
                "datatype": [r["datatype"].value for r in rows],
            }
        )

    def get_error_object_types(self) -> set[str]:
        rows = self._storage.query("SELECT type_name FROM nature.object_type WHERE objclass = 'err'")
        return {str(row["type_name"]) for row in rows}

    def get_modified_object_pgcs(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._storage.query(
            """
            SELECT p.id AS pgc
            FROM common.pgc AS p
            WHERE p.modification_time > %s
              AND p.id > %s
              AND (
                EXISTS (
                  SELECT 1
                  FROM layer0.records AS o
                  JOIN designation.data AS d ON d.record_id = o.id
                  WHERE o.pgc = p.id
                )
                OR EXISTS (
                  SELECT 1
                  FROM layer0.records AS o
                  JOIN nature.data AS n ON n.record_id = o.id
                  WHERE o.pgc = p.id
                )
                OR EXISTS (
                  SELECT 1
                  FROM layer0.records AS o
                  JOIN icrs.data AS i ON i.record_id = o.id
                  WHERE o.pgc = p.id
                )
              )
            ORDER BY p.id
            LIMIT %s
            """,
            params=[dt, offset, limit],
        )
        return table.QTable({"pgc": [int(row["pgc"]) for row in rows]})

    def get_designation_records_for_pgcs(
        self,
        pgcs: list[int],
        priority_masks: Sequence[str],
    ) -> table.QTable:
        if not pgcs:
            return table.QTable({"pgc": [], "design": []})
        priority_case = "\n".join(
            [
                "CASE",
                *[f"  WHEN l1.design ~ '^{mask}$' THEN {i}" for i, mask in enumerate(priority_masks)],
                f"  ELSE {len(priority_masks)}",
                "END",
            ]
        )
        rows = self._storage.query(
            f"""
            WITH ranked AS (
              SELECT
                o.pgc,
                l1.design,
                {priority_case} AS prio
              FROM designation.data AS l1
              JOIN layer0.records AS o ON l1.record_id = o.id
              WHERE o.pgc = ANY(%s)
            ),
            best AS (
              SELECT pgc, MIN(prio) AS prio
              FROM ranked
              GROUP BY pgc
            ),
            filtered AS (
              SELECT r.pgc, r.design
              FROM ranked AS r
              JOIN best AS b ON b.pgc = r.pgc AND b.prio = r.prio
            ),
            counted AS (
              SELECT
                pgc,
                design,
                ROW_NUMBER() OVER (
                  PARTITION BY pgc
                  ORDER BY COUNT(*) DESC, design
                ) AS rn
              FROM filtered
              GROUP BY pgc, design
            )
            SELECT pgc, design
            FROM counted
            WHERE rn = 1
            ORDER BY pgc
            """,
            params=[pgcs],
        )
        return table.QTable(
            {
                "pgc": [int(row["pgc"]) for row in rows],
                "design": [row["design"] for row in rows],
            }
        )

    def get_nature_records_for_pgcs(self, pgcs: list[int]) -> table.QTable:
        if not pgcs:
            return table.QTable({"pgc": [], "type_name": []})
        rows = self._storage.query(
            """
            WITH counted AS (
              SELECT
                o.pgc,
                l1.type_name,
                ROW_NUMBER() OVER (
                  PARTITION BY o.pgc
                  ORDER BY COUNT(*) DESC, l1.type_name
                ) AS rn
              FROM nature.data AS l1
              JOIN layer0.records AS o ON l1.record_id = o.id
              WHERE o.pgc = ANY(%s)
              GROUP BY o.pgc, l1.type_name
            )
            SELECT pgc, type_name
            FROM counted
            WHERE rn = 1
            ORDER BY pgc
            """,
            params=[pgcs],
        )
        return table.QTable(
            {
                "pgc": [int(row["pgc"]) for row in rows],
                "type_name": [row["type_name"] for row in rows],
            }
        )

    def get_layer2_icrs(self, pgcs: list[int]) -> table.QTable:
        empty = table.QTable({"pgc": [], "ra": [], "e_ra": [], "dec": [], "e_dec": []})
        if not pgcs:
            return empty
        rows = self._storage.query(
            """
            SELECT pgc, ra, e_ra, dec, e_dec
            FROM layer2.icrs
            WHERE pgc = ANY(%s)
            ORDER BY pgc
            """,
            params=[pgcs],
        )
        if not rows:
            return empty
        icrs_info = self.get_table_metadata("layer2", "icrs")
        units = {name: col.unit for name, col in icrs_info.columns.items() if col.unit}
        return table.QTable(
            {
                "pgc": [int(row["pgc"]) for row in rows],
                "ra": u.Quantity([float(row["ra"]) for row in rows], u.Unit(units["ra"])),
                "e_ra": u.Quantity([float(row["e_ra"]) for row in rows], u.Unit(units["e_ra"])),
                "dec": u.Quantity([float(row["dec"]) for row in rows], u.Unit(units["dec"])),
                "e_dec": u.Quantity([float(row["e_dec"]) for row in rows], u.Unit(units["e_dec"])),
            }
        )

    def get_icrs_records_for_pgcs(self, pgcs: list[int]) -> table.QTable:
        empty = table.QTable({"pgc": [], "ra": [], "e_ra": [], "dec": [], "e_dec": []})
        if not pgcs:
            return empty
        rows = self._storage.query(
            """
            WITH src AS (
              SELECT o.pgc, l1.ra, l1.e_ra, l1.dec, l1.e_dec, t.datatype
              FROM icrs.data AS l1
              JOIN layer0.records AS o ON l1.record_id = o.id
              JOIN layer0.tables AS t ON o.table_id = t.id
              WHERE o.pgc = ANY(%s)
            ),
            filtered AS (
              SELECT s.pgc, s.ra, s.e_ra, s.dec, s.e_dec
              FROM src AS s
              WHERE s.datatype <> 'compilation'
                 OR NOT EXISTS (
                   SELECT 1
                   FROM src AS s2
                   WHERE s2.pgc = s.pgc AND s2.datatype <> 'compilation'
                 )
            )
            SELECT
              pgc,
              SUM(ra / (e_ra * e_ra)) / SUM(1.0 / (e_ra * e_ra)) AS ra,
              1.0 / SQRT(SUM(1.0 / (e_ra * e_ra))) AS e_ra,
              SUM(dec / (e_dec * e_dec)) / SUM(1.0 / (e_dec * e_dec)) AS dec,
              1.0 / SQRT(SUM(1.0 / (e_dec * e_dec))) AS e_dec
            FROM filtered
            GROUP BY pgc
            ORDER BY pgc
            """,
            params=[pgcs],
        )
        if not rows:
            return empty
        icrs_table = layer1.get_catalog_object_type(layer1.Catalog.ICRS).layer1_table()
        icrs_schema, icrs_name = icrs_table.split(".", maxsplit=1)
        icrs_info = self.get_table_metadata(icrs_schema, icrs_name)
        units = {name: col.unit for name, col in icrs_info.columns.items() if col.unit}
        return table.QTable(
            {
                "pgc": [int(row["pgc"]) for row in rows],
                "ra": u.Quantity([float(row["ra"]) for row in rows], u.Unit(units["ra"])),
                "e_ra": u.Quantity([float(row["e_ra"]) for row in rows], u.Unit(units["e_ra"])),
                "dec": u.Quantity([float(row["dec"]) for row in rows], u.Unit(units["dec"])),
                "e_dec": u.Quantity([float(row["e_dec"]) for row in rows], u.Unit(units["e_dec"])),
            }
        )

    def get_new_designation_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records("designation.data", "l1.design", dt, limit, offset)
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "design": [r["design"] for r in rows],
            }
        )

    def get_table_metadata(self, schema: str, table: str) -> postgres.TableInfo:
        return postgres.get_table_metadata(self._storage, schema, table)

    def get_table_record_count(self, table_name: str) -> int:
        layer0.require_table_id(self._storage, table_name)
        row = self._get_table_progress_funnel([table_name]).get(table_name)
        if row is None:
            return 0
        return int(row["total_records"])

    def fetch_rawdata_batch(
        self,
        table_name: str,
        columns: Sequence[str],
        limit: int,
        offset: str,
    ) -> list[dict[str, Any]]:
        query, params = layer0.build_raw_table_select(
            table_name,
            columns=[layer0.INTERNAL_ID_COLUMN_NAME, *columns],
            offset=offset,
            order_column=layer0.INTERNAL_ID_COLUMN_NAME,
            order_direction="asc",
            limit=limit,
        )
        return list(self._storage.query(query, params=params))

    def save_structured_data(
        self,
        catalog: layer1.Catalog,
        columns: Sequence[str],
        ids: Sequence[str],
        data: list[list[Any]],
    ) -> None:
        object_cls = layer1.get_catalog_object_type(catalog)
        normalized = layer1.normalize_catalog_rows(catalog, columns, [list(row) for row in data])
        try:
            with self.with_tx():
                layer1.save_structured_data(
                    self._storage,
                    object_cls.layer1_table(),
                    columns,
                    ids,
                    normalized,
                    object_cls.layer1_primary_keys(),
                )
        except psycopg.errors.ForeignKeyViolation as e:
            raise RuntimeError(layer1.format_foreign_key_violation(e)) from e

    def _query_new_pgc_records(
        self,
        layer1_table: str,
        select_columns: str,
        dt: datetime.datetime,
        limit: int,
        offset: int,
        extra_joins: str = "",
    ) -> list[dict[str, Any]]:
        query = f"""SELECT o.pgc, {select_columns}
        FROM {layer1_table} AS l1
        JOIN layer0.records AS o ON l1.record_id = o.id
        {extra_joins}
        WHERE o.pgc IN (
            SELECT DISTINCT o.pgc
            FROM {layer1_table} AS l1
            JOIN layer0.records AS o ON l1.record_id = o.id
            JOIN common.pgc AS p ON p.id = o.pgc
            WHERE p.modification_time > %s AND o.pgc > %s
            ORDER BY o.pgc
            LIMIT %s
        )
        ORDER BY o.pgc ASC"""
        return self._storage.query(query, params=[dt, offset, limit])

    def list_tables_needing_statistics_refresh(self) -> list[tuple[str, datetime.datetime]]:
        rows = self._storage.query(
            """
            SELECT table_name, modification_dt
            FROM layer0.tables
            WHERE statistics_refresh_dt IS NULL OR modification_dt > statistics_refresh_dt
            ORDER BY table_name
            """
        )
        return [(row["table_name"], row["modification_dt"]) for row in rows]

    def save_table_statistics(
        self,
        table_name: str,
        progress: table_statistics.TableProgress,
        observed_modification_dt: datetime.datetime,
    ) -> None:
        self._storage.exec(
            """
            UPDATE layer0.tables
            SET statistics = %s::jsonb, statistics_refresh_dt = %s
            WHERE table_name = %s
            """,
            params=[_statistics_to_json(progress), observed_modification_dt, table_name],
        )

    def get_column_progress(self, table_name: str) -> dict[str, table_statistics.ColumnProgress]:
        meta = self.get_table_metadata(layer0.RAWDATA_SCHEMA, table_name)
        columns = [
            (name, info.data_type) for name, info in meta.columns.items() if name != layer0.INTERNAL_ID_COLUMN_NAME
        ]
        if not columns:
            return {}

        select_parts: list[sql.Composable] = []
        for index, (name, data_type) in enumerate(columns):
            select_parts.append(
                sql.SQL("COUNT({}) AS {}").format(sql.Identifier(name), sql.Identifier(f"__nn_{index}"))
            )
            if _supports_min_max(data_type):
                select_parts.append(
                    sql.SQL("MIN({}) AS {}").format(sql.Identifier(name), sql.Identifier(f"__min_{index}"))
                )
                select_parts.append(
                    sql.SQL("MAX({}) AS {}").format(sql.Identifier(name), sql.Identifier(f"__max_{index}"))
                )

        query = sql.SQL("SELECT {} FROM {}.{}").format(
            sql.SQL(", ").join(select_parts),
            sql.Identifier(layer0.RAWDATA_SCHEMA),
            sql.Identifier(table_name),
        )
        row = self._storage.query_one(query)

        result: dict[str, table_statistics.ColumnProgress] = {}
        for index, (name, data_type) in enumerate(columns):
            min_value: table_statistics.StatValue | None = None
            max_value: table_statistics.StatValue | None = None
            if _supports_min_max(data_type):
                min_value = _stat_value(row[f"__min_{index}"])
                max_value = _stat_value(row[f"__max_{index}"])
            result[name] = table_statistics.ColumnProgress(
                non_null_count=int(row[f"__nn_{index}"]),
                min=min_value,
                max=max_value,
            )
        return result

    def get_table_progress(
        self,
        table_names: list[str] | None = None,
    ) -> dict[str, table_statistics.TableProgress]:
        catalogs = list(layer1.Catalog)
        catalog_names = [catalog.value for catalog in catalogs]

        errgr = concurrency.ErrorGroup()
        funnel_task = errgr.run(self._get_table_progress_funnel, table_names)
        catalog_tasks = {catalog: errgr.run(self._get_catalog_progress, catalog, table_names) for catalog in catalogs}
        errgr.wait()

        funnel = funnel_task.result()
        empty_catalogs = {name: table_statistics.CatalogProgress(structured=0) for name in catalog_names}

        result: dict[str, table_statistics.TableProgress] = {
            table_name: table_statistics.TableProgress(
                total_records=int(row["total_records"]),
                unprocessed=int(row["unprocessed"]),
                pending_triage=int(row["pending_triage"]),
                resolved_unsubmitted=int(row["resolved_unsubmitted"]),
                submitted=int(row["submitted"]),
                catalogs=dict(empty_catalogs),
            )
            for table_name, row in funnel.items()
        }

        for catalog in catalogs:
            catalog_rows = catalog_tasks[catalog].result()
            alias = catalog.value
            for table_name, catalog_progress in catalog_rows.items():
                if table_name not in result:
                    result[table_name] = table_statistics.TableProgress(
                        total_records=0,
                        unprocessed=0,
                        pending_triage=0,
                        resolved_unsubmitted=0,
                        submitted=0,
                        catalogs=dict(empty_catalogs),
                    )
                result[table_name].catalogs[alias] = catalog_progress

        return result

    def _get_table_progress_funnel(self, table_names: list[str] | None) -> dict[str, dict[str, Any]]:
        where_clause, params = _progress_table_filter(table_names)
        rows = self._storage.query(
            f"""
            SELECT t.table_name,
                   COUNT(*) AS total_records,
                   COUNT(*) FILTER (WHERE c.record_id IS NULL) AS unprocessed,
                   COUNT(*) FILTER (
                       WHERE c.record_id IS NOT NULL AND c.triage_status = 'pending'
                   ) AS pending_triage,
                   COUNT(*) FILTER (
                       WHERE c.triage_status = 'resolved' AND r.pgc IS NULL
                   ) AS resolved_unsubmitted,
                   COUNT(*) FILTER (WHERE r.pgc IS NOT NULL) AS submitted
            FROM layer0.records AS r
            JOIN layer0.tables AS t ON r.table_id = t.id
            LEFT JOIN layer0.crossmatch AS c ON c.record_id = r.id
            {where_clause}
            GROUP BY t.table_name, t.id
            ORDER BY t.table_name
            """,
            params=params,
        )
        return {row["table_name"]: row for row in rows}

    def _get_catalog_progress(
        self,
        catalog: layer1.Catalog,
        table_names: list[str] | None,
    ) -> dict[str, table_statistics.CatalogProgress]:
        object_cls = layer1.get_catalog_object_type(catalog)
        layer1_table = object_cls.layer1_table()
        where_clause, params = _progress_table_filter(table_names)
        rows = self._storage.query(
            f"""
            SELECT t.table_name, COUNT(*) AS structured
            FROM (
                SELECT DISTINCT record_id
                FROM {layer1_table}
            ) AS d
            JOIN layer0.records AS r ON r.id = d.record_id
            JOIN layer0.tables AS t ON r.table_id = t.id
            {where_clause}
            GROUP BY t.table_name, t.id
            """,
            params=params,
        )
        return {row["table_name"]: table_statistics.CatalogProgress(structured=int(row["structured"])) for row in rows}


def _statistics_to_json(progress: table_statistics.TableProgress) -> str:
    payload = {
        "total_records": progress.total_records,
        "unprocessed": progress.unprocessed,
        "pending_triage": progress.pending_triage,
        "resolved_unsubmitted": progress.resolved_unsubmitted,
        "submitted": progress.submitted,
        "catalogs": {name: {"structured": catalog.structured} for name, catalog in progress.catalogs.items()},
        "columns": {
            name: {
                "non_null_count": column.non_null_count,
                "min": column.min,
                "max": column.max,
            }
            for name, column in progress.columns.items()
        },
    }
    return json.dumps(payload)


def _supports_min_max(data_type: str) -> bool:
    return mapping.type_map.get(data_type, data_type) in _MIN_MAX_TYPES


def _stat_value(value: Any) -> table_statistics.StatValue | None:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if hasattr(value, "item"):
        return _stat_value(value.item())
    return str(value)


def _progress_table_filter(table_names: list[str] | None) -> tuple[str, list[Any]]:
    if table_names is None:
        return "", []
    return "WHERE t.table_name = ANY(%s)", [table_names]


def _column_as_list(col: Any) -> list[Any]:
    if getattr(col, "unit", None) is not None:
        return col.value.tolist()
    return [v.item() if hasattr(v, "item") else v for v in col]
