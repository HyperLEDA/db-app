import json
from collections.abc import Sequence
from typing import Any

from app.data import model, template
from app.lib import concurrency
from app.lib.storage import enums, postgres


def _metadata_to_candidates(metadata: dict[str, Any] | None) -> list[int]:
    if metadata is None:
        return []
    if "pgc" in metadata and metadata["pgc"] is not None:
        return [int(metadata["pgc"])]
    if "possible_matches" in metadata and metadata["possible_matches"] is not None:
        return [int(p) for p in metadata["possible_matches"]]
    return []


def _candidates_to_metadata(candidates: list[int]) -> dict[str, Any]:
    if len(candidates) == 0:
        return {}
    if len(candidates) == 1:
        return {"pgc": candidates[0]}
    return {"possible_matches": candidates}


class AssignRecordPgcsPreconditionError(Exception):
    def __init__(self, sample: list[str], count: int) -> None:
        self.sample = sample
        self.count = count


class Layer0RecordRepository(postgres.TransactionalPGRepository):
    def register_records(self, table_name: str, record_ids: list[str]) -> None:
        if len(record_ids) == 0:
            raise RuntimeError("no records to upsert")

        table_id_row = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])

        table_id = table_id_row["id"]

        query = (
            "INSERT INTO layer0.records (id, table_id) VALUES (%s, %s) "
            "ON CONFLICT (id) DO UPDATE SET table_id = EXCLUDED.table_id"
        )
        rows = [[record_id, table_id] for record_id in record_ids]
        self._storage.execute_batch(query, rows)

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
        params: list[Any] = []

        where_stmnt = []
        join_tables = """
            FROM layer0.records AS o
            JOIN layer0.crossmatch AS c ON o.id = c.record_id
        """

        if table_name is not None:
            join_tables += " JOIN layer0.tables AS t ON o.table_id = t.id"
            where_stmnt.append("t.table_name = %s")
            params.append(table_name)

        if offset is not None:
            where_stmnt.append("o.id > %s")
            params.append(offset)

        if status is not None:
            statuses = list(status)
            if statuses:
                status_values = [s.value for s in statuses]
                where_stmnt.append(
                    "((c.metadata::jsonb = '{}'::jsonb AND 'new' = ANY(%s)) OR "
                    "(c.metadata::jsonb ? 'pgc' AND 'existing' = ANY(%s)) OR "
                    "(c.metadata::jsonb ? 'possible_matches' AND 'collided' = ANY(%s)))"
                )
                params.extend([status_values, status_values, status_values])

        if triage_status is not None:
            triage_statuses = list(triage_status)
            if triage_statuses:
                where_stmnt.append("c.triage_status = ANY(%s)")
                params.append([s.value for s in triage_statuses])

        if record_id is not None:
            where_stmnt.append("o.id = %s")
            params.append(record_id)

        where_clause = f"WHERE {' AND '.join(where_stmnt)}" if where_stmnt else ""

        query = f"""SELECT o.id, c.triage_status, c.metadata
            {join_tables}
            {where_clause}
            ORDER BY o.id
            LIMIT %s"""
        params.append(limit)

        if row_offset is not None:
            query += " OFFSET %s"
            params.append(row_offset)

        rows = self._storage.query(query, params=params)

        return [
            model.CrossmatchRecordRow(
                record_id=row["id"],
                triage_status=row["triage_status"],
                candidates=_metadata_to_candidates(row["metadata"]),
            )
            for row in rows
        ]

    def set_crossmatch_results(self, rows: list[tuple[str, enums.RecordTriageStatus, list[int]]]) -> None:
        if not rows:
            return
        query = (
            "INSERT INTO layer0.crossmatch (record_id, triage_status, metadata) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (record_id) DO UPDATE SET "
            "triage_status = EXCLUDED.triage_status, metadata = EXCLUDED.metadata"
        )
        db_rows = [
            (record_id, triage.value, json.dumps(_candidates_to_metadata(candidates)))
            for record_id, triage, candidates in rows
        ]
        with self.with_tx():
            cursor = self._storage.get_connection().cursor()
            cursor.executemany(query, db_rows)

    def assign_record_pgcs(self, record_ids: list[str]) -> None:
        if not record_ids:
            return

        with self.with_tx():
            conn = self._storage.get_connection()
            cur = conn.cursor()
            cur.execute("CREATE TEMP TABLE submit_staging (record_id text PRIMARY KEY) ON COMMIT DROP")
            with cur.copy("COPY submit_staging (record_id) FROM STDIN") as copy:
                for record_id in record_ids:
                    copy.write_row((record_id,))

            invalid_rows = self._storage.query(
                """
                SELECT s.record_id::text AS record_id
                FROM submit_staging s
                LEFT JOIN layer0.crossmatch c ON c.record_id = s.record_id
                WHERE c.record_id IS NULL
                   OR c.triage_status != 'resolved'
                   OR c.metadata::jsonb ? 'possible_matches'
                LIMIT 101
                """
            )
            if invalid_rows:
                count_row = self._storage.query_one(
                    """
                    SELECT COUNT(*)::int AS cnt
                    FROM submit_staging s
                    LEFT JOIN layer0.crossmatch c ON c.record_id = s.record_id
                    WHERE c.record_id IS NULL
                       OR c.triage_status != 'resolved'
                       OR c.metadata::jsonb ? 'possible_matches'
                    """
                )
                raise AssignRecordPgcsPreconditionError(
                    sample=[row["record_id"] for row in invalid_rows[:100]],
                    count=int(count_row["cnt"]),
                )

            self._storage.query(
                """
                SELECT s.record_id
                FROM submit_staging s
                JOIN layer0.crossmatch c ON c.record_id = s.record_id
                JOIN layer0.records r ON r.id = s.record_id
                FOR UPDATE OF c, r
                """
            )

            existing_rows = self._storage.query(
                """
                SELECT s.record_id::text AS record_id, (c.metadata->>'pgc')::int AS pgc
                FROM submit_staging s
                JOIN layer0.crossmatch c ON c.record_id = s.record_id
                JOIN layer0.records r ON r.id = s.record_id
                WHERE c.metadata::jsonb ? 'pgc'
                  AND r.pgc IS NULL
                ORDER BY s.record_id
                """
            )
            new_rows = self._storage.query(
                """
                SELECT s.record_id::text AS record_id
                FROM submit_staging s
                JOIN layer0.crossmatch c ON c.record_id = s.record_id
                JOIN layer0.records r ON r.id = s.record_id
                WHERE c.metadata::jsonb = '{}'::jsonb
                  AND r.pgc IS NULL
                ORDER BY s.record_id
                """
            )

            pgcs_to_insert: dict[str, int] = {row["record_id"]: int(row["pgc"]) for row in existing_rows}

            if new_rows:
                minted = self._storage.query(
                    f"""INSERT INTO common.pgc
                    VALUES {",".join(["(DEFAULT)"] * len(new_rows))}
                    RETURNING id"""
                )
                for row, minted_row in zip(new_rows, minted, strict=True):
                    pgcs_to_insert[row["record_id"]] = int(minted_row["id"])

            if pgcs_to_insert:
                update_query = (
                    "UPDATE layer0.records SET pgc = v.pgc "
                    "FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
                    "WHERE layer0.records.id = v.record_id AND layer0.records.pgc IS NULL"
                )
                rows = [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()]
                self._storage.execute_batch(update_query, rows)

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        pgcs_to_insert: dict[str, int] = {}

        new_records = [record_id for record_id, pgc in pgcs.items() if pgc is None]

        if new_records:
            result = self._storage.query(
                f"""INSERT INTO common.pgc 
                VALUES {",".join(["(DEFAULT)"] * len(new_records))} 
                RETURNING id""",
            )

            ids = [row["id"] for row in result]

            for record_id, pgc_id in zip(new_records, ids, strict=False):
                pgcs_to_insert[record_id] = pgc_id

        for record_id, pgc in pgcs.items():
            if pgc is not None:
                pgcs_to_insert[record_id] = pgc

        if pgcs_to_insert:
            update_query = (
                "UPDATE layer0.records SET pgc = v.pgc FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
                "WHERE layer0.records.id = v.record_id"
            )
            rows = [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()]
            self._storage.execute_batch(update_query, rows)

    def _progress_table_filter(self, table_names: list[str] | None) -> tuple[str, list[Any]]:
        if table_names is None:
            return "", []
        return "WHERE t.table_name = ANY(%s)", [table_names]

    def _progress_catalogs(self) -> list[model.RawCatalog]:
        catalogs: list[model.RawCatalog] = []
        for catalog in model.RawCatalog:
            if catalog in model.RUNTIME_RAW_CATALOGS:
                continue
            try:
                model.get_catalog_object_type(catalog)
            except ValueError:
                continue
            catalogs.append(catalog)
        return catalogs

    def _get_table_progress_funnel(self, table_names: list[str] | None) -> dict[str, dict[str, Any]]:
        where_clause, params = self._progress_table_filter(table_names)
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
        catalog: model.RawCatalog,
        table_names: list[str] | None,
    ) -> dict[str, model.CatalogProgress]:
        object_cls = model.get_catalog_object_type(catalog)
        layer1_table = object_cls.layer1_table()
        where_clause, params = self._progress_table_filter(table_names)

        try:
            layer2_table = object_cls.layer2_table()
        except NotImplementedError:
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
            return {
                row["table_name"]: model.CatalogProgress(
                    structured=int(row["structured"]),
                    in_layer2=0,
                    layer2_pending=0,
                )
                for row in rows
            }

        rows = self._storage.query(
            f"""
            SELECT t.table_name,
                   COUNT(*) AS structured,
                   COUNT(*) FILTER (
                       WHERE r.pgc IS NOT NULL AND l2.pgc IS NOT NULL
                   ) AS in_layer2,
                   COUNT(*) FILTER (
                       WHERE r.pgc IS NOT NULL
                         AND (l2.pgc IS NULL OR r.modification_time > lu.dt)
                   ) AS layer2_pending
            FROM (
                SELECT DISTINCT record_id
                FROM {layer1_table}
            ) AS d
            JOIN layer0.records AS r ON r.id = d.record_id
            JOIN layer0.tables AS t ON r.table_id = t.id
            LEFT JOIN {layer2_table} AS l2 ON l2.pgc = r.pgc
            CROSS JOIN (
                SELECT dt
                FROM layer2.last_update
                WHERE catalog = %s
            ) AS lu
            {where_clause}
            GROUP BY t.table_name, t.id
            """,
            params=[catalog.value, *params],
        )
        return {
            row["table_name"]: model.CatalogProgress(
                structured=int(row["structured"]),
                in_layer2=int(row["in_layer2"]),
                layer2_pending=int(row["layer2_pending"]),
            )
            for row in rows
        }

    def get_table_progress(self, table_names: list[str] | None = None) -> dict[str, model.TableProgress]:
        catalogs = self._progress_catalogs()
        catalog_names = [catalog.value for catalog in catalogs]

        errgr = concurrency.ErrorGroup()
        funnel_task = errgr.run(self._get_table_progress_funnel, table_names)
        catalog_tasks = {catalog: errgr.run(self._get_catalog_progress, catalog, table_names) for catalog in catalogs}
        errgr.wait()

        funnel = funnel_task.result()
        empty_catalogs = {
            name: model.CatalogProgress(structured=0, in_layer2=0, layer2_pending=0) for name in catalog_names
        }

        result: dict[str, model.TableProgress] = {
            table_name: model.TableProgress(
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
                    result[table_name] = model.TableProgress(
                        total_records=0,
                        unprocessed=0,
                        pending_triage=0,
                        resolved_unsubmitted=0,
                        submitted=0,
                        catalogs=dict(empty_catalogs),
                    )
                result[table_name].catalogs[alias] = catalog_progress

        return result
