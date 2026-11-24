import contextvars
from concurrent import futures
from typing import Any

from psycopg import sql

from app.catalogs.layer0 import rawdata_table, require_table_id, touch_pgcs
from app.lib.crossmatch import data as crossmatch_data
from app.lib.crossmatch import query as crossmatch_query
from app.lib.crossmatch.query import filtered_record_count, filtered_record_sample, filtered_tablesample
from app.lib.storage import enums, postgres

_TABLESAMPLE_MIN_ROWS_PER_LIMIT = 100
_TABLESAMPLE_OVERSAMPLING = 3
_TABLESAMPLE_RETRY_FACTOR = 4
_CROSSMATCH_INPUT_STREAMS = 4
_CROSSMATCH_INPUT_MIN_CHUNK = 100


class AssignRecordPgcsPreconditionError(Exception):
    def __init__(self, sample: list[str], count: int) -> None:
        self.sample = sample
        self.count = count


class Layer0RecordRepository(postgres.TransactionalPGRepository):
    def register_records(self, table_name: str, record_ids: list[str]) -> None:
        if len(record_ids) == 0:
            raise RuntimeError("no records to upsert")

        with rawdata_table(self._storage, table_name=table_name) as table_ids:
            table_id = table_ids[0]
            with self._storage.get_connection().cursor() as cur:
                cur.execute("CREATE TEMP TABLE records_staging (id text, table_id int) ON COMMIT DROP")
                with cur.copy("COPY records_staging (id, table_id) FROM STDIN") as copy:
                    for record_id in record_ids:
                        copy.write_row((record_id, table_id))
                cur.execute(
                    """
                    INSERT INTO layer0.records (id, table_id)
                    SELECT id, table_id FROM records_staging
                    ON CONFLICT (id) DO UPDATE SET table_id = EXCLUDED.table_id
                    """
                )

    def set_crossmatch_results(self, rows: list[tuple[str, enums.RecordTriageStatus, list[int]]]) -> None:
        if not rows:
            return
        with self.with_tx():
            with rawdata_table(self._storage, record_ids=[record_id for record_id, _, _ in rows]):
                crossmatch_data.write_crossmatch_rows(self._storage, rows)

    def assign_record_pgcs(self, record_ids: list[str]) -> None:
        if not record_ids:
            return

        invalid_where = """
            FROM submit_staging s
            LEFT JOIN layer0.crossmatch c ON c.record_id = s.record_id
            WHERE c.record_id IS NULL
               OR c.triage_status != 'resolved'
               OR c.metadata::jsonb ? 'possible_matches'
               OR (
                    jsonb_typeof(c.metadata::jsonb -> 'candidates') = 'array'
                    AND jsonb_array_length(c.metadata::jsonb -> 'candidates') > 1
               )
        """
        join_submit = """
            FROM submit_staging s
            JOIN layer0.crossmatch c ON c.record_id = s.record_id
            JOIN layer0.records r ON r.id = s.record_id
        """
        with self.with_tx():
            with self._storage.get_connection().cursor() as cur:
                cur.execute("CREATE TEMP TABLE submit_staging (record_id text PRIMARY KEY) ON COMMIT DROP")
                with cur.copy("COPY submit_staging (record_id) FROM STDIN") as copy:
                    for record_id in record_ids:
                        copy.write_row((record_id,))

            invalid_rows = self._storage.query(f"SELECT s.record_id::text AS record_id {invalid_where} LIMIT 101")
            if invalid_rows:
                count_row = self._storage.query_one(f"SELECT COUNT(*)::int AS cnt {invalid_where}")
                raise AssignRecordPgcsPreconditionError(
                    sample=[row["record_id"] for row in invalid_rows[:100]],
                    count=int(count_row["cnt"]),
                )

            self._storage.query(f"SELECT s.record_id {join_submit} FOR UPDATE OF c, r")
            existing_rows = self._storage.query(
                f"""
                SELECT s.record_id::text AS record_id,
                       CASE
                           WHEN jsonb_typeof(c.metadata::jsonb -> 'candidates') = 'array'
                                AND jsonb_array_length(c.metadata::jsonb -> 'candidates') = 1
                               THEN (c.metadata::jsonb -> 'candidates' -> 0 ->> 'pgc')::int
                           ELSE (c.metadata->>'pgc')::int
                       END AS pgc
                {join_submit}
                WHERE r.pgc IS NULL
                  AND (
                        (
                            jsonb_typeof(c.metadata::jsonb -> 'candidates') = 'array'
                            AND jsonb_array_length(c.metadata::jsonb -> 'candidates') = 1
                        )
                        OR c.metadata::jsonb ? 'pgc'
                  )
                ORDER BY s.record_id
                """
            )
            new_rows = self._storage.query(
                f"""
                SELECT s.record_id::text AS record_id
                {join_submit}
                WHERE c.metadata::jsonb = '{{}}'::jsonb AND r.pgc IS NULL
                ORDER BY s.record_id
                """
            )

            pgcs_to_insert = {row["record_id"]: int(row["pgc"]) for row in existing_rows}
            if new_rows:
                for row, pgc_id in zip(new_rows, self._mint_pgc_ids(len(new_rows)), strict=True):
                    pgcs_to_insert[row["record_id"]] = pgc_id
            if pgcs_to_insert:
                with rawdata_table(self._storage, record_ids=list(pgcs_to_insert.keys())):
                    self._storage.execute_batch(
                        "UPDATE layer0.records SET pgc = v.pgc "
                        "FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
                        "WHERE layer0.records.id = v.record_id AND layer0.records.pgc IS NULL",
                        [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()],
                    )
                    touch_pgcs(self._storage, list(set(pgcs_to_insert.values())))

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        pgcs_to_insert = {record_id: pgc for record_id, pgc in pgcs.items() if pgc is not None}
        new_records = [record_id for record_id, pgc in pgcs.items() if pgc is None]
        if new_records:
            shared_pgc = self._mint_pgc_ids(1)[0]
            for record_id in new_records:
                pgcs_to_insert[record_id] = shared_pgc
        if not pgcs_to_insert:
            return
        with rawdata_table(self._storage, record_ids=list(pgcs_to_insert.keys())):
            previous_pgcs = {
                int(row["pgc"])
                for row in self._storage.query(
                    "SELECT pgc FROM layer0.records WHERE id = ANY(%s) AND pgc IS NOT NULL",
                    params=[list(pgcs_to_insert.keys())],
                )
            }
            self._storage.execute_batch(
                "UPDATE layer0.records SET pgc = v.pgc FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
                "WHERE layer0.records.id = v.record_id",
                [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()],
            )
            touch_pgcs(self._storage, list(previous_pgcs | set(pgcs_to_insert.values())))

    def _mint_pgc_ids(self, count: int) -> list[int]:
        rows = self._storage.query(
            f"""INSERT INTO common.pgc (id)
            VALUES {",".join(["(DEFAULT)"] * count)}
            RETURNING id"""
        )
        return [int(row["id"]) for row in rows]

    def merge_pgcs(self, target_pgc: int, source_pgcs: list[int]) -> int:
        rows = self._storage.query(
            """
            UPDATE layer0.records
            SET pgc = %s
            WHERE pgc = ANY(%s)
            RETURNING id
            """,
            params=[target_pgc, source_pgcs],
        )
        with rawdata_table(self._storage, record_ids=[row["id"] for row in rows]):
            touch_pgcs(self._storage, [target_pgc, *source_pgcs])
        return len(rows)

    def sample_crossmatch_records(
        self,
        table_name: str,
        limit: int,
        row_filter: sql.Composable | None = None,
    ) -> tuple[list[str], int, int]:
        table_id = require_table_id(self._storage, table_name)
        total = int(
            self._storage.query_one(
                "SELECT COUNT(*) AS cnt FROM layer0.records WHERE table_id = %s",
                params=[table_id],
            )["cnt"]
        )
        if total == 0:
            return [], 0, 0

        if row_filter is None:
            eligible = total
            if eligible < _TABLESAMPLE_MIN_ROWS_PER_LIMIT * limit:
                rows = self._storage.query(
                    "SELECT id FROM layer0.records WHERE table_id = %s ORDER BY random() LIMIT %s",
                    params=[table_id, limit],
                    read_only=True,
                )
                return [str(row["id"]) for row in rows], eligible, total

            percent = min(100.0, 100.0 * _TABLESAMPLE_OVERSAMPLING * limit / eligible)
            query = """
                SELECT id FROM layer0.records TABLESAMPLE SYSTEM (%s)
                WHERE table_id = %s
                ORDER BY random()
                LIMIT %s
            """
            while True:
                rows = self._storage.query(query, params=[percent, table_id, limit], read_only=True)
                if len(rows) >= limit or percent >= 100.0:
                    return [str(row["id"]) for row in rows], eligible, total
                percent = min(100.0, percent * _TABLESAMPLE_RETRY_FACTOR)

        if total < _TABLESAMPLE_MIN_ROWS_PER_LIMIT * limit:
            eligible = int(
                self._storage.query_one(filtered_record_count(table_name, row_filter), params=[table_id])["cnt"]
            )
            if eligible == 0:
                return [], 0, total
            rows = self._storage.query(
                filtered_record_sample(table_name, row_filter),
                params=[table_id, limit],
                read_only=True,
            )
            return [str(row["id"]) for row in rows], eligible, total

        # The eligible count is estimated from the sample: an exact filtered count scans the whole table.
        percent = min(100.0, 100.0 * _TABLESAMPLE_OVERSAMPLING * limit / total)
        query = filtered_tablesample(table_name, row_filter)
        while True:
            row = self._storage.query(query, params=[percent, limit], read_only=True)[0]
            scanned, passing = int(row["scanned"]), int(row["passing"])
            if passing >= limit or percent >= 100.0:
                eligible = passing if percent >= 100.0 else round(total * passing / max(scanned, 1))
                return [str(record_id) for record_id in row["ids"]], eligible, total
            percent = min(100.0, percent * _TABLESAMPLE_RETRY_FACTOR)

    def fetch_crossmatch_inputs(
        self,
        table_name: str,
        record_ids: list[str],
        pgc_column: str | None,
        radius_deg: float,
        *,
        include_redshift: bool,
        include_nature: bool,
    ) -> list[dict[str, Any]]:
        if not record_ids:
            return []
        bulk = len(record_ids) > crossmatch_query.BULK_THRESHOLD
        query = crossmatch_query.crossmatch_input(
            crossmatch_query.id_records(table_name, pgc_column),
            include_redshift=include_redshift,
            include_nature=include_nature,
            bulk=bulk,
        )
        if bulk or len(record_ids) < _CROSSMATCH_INPUT_MIN_CHUNK * 2:
            return self._fetch_crossmatch_inputs(query, record_ids, radius_deg, bulk=bulk)

        # The index path is bound by random reads; on HDD a few concurrent streams overlap the seeks.
        chunks = [record_ids[i::_CROSSMATCH_INPUT_STREAMS] for i in range(_CROSSMATCH_INPUT_STREAMS)]
        with futures.ThreadPoolExecutor(max_workers=_CROSSMATCH_INPUT_STREAMS) as executor:
            # Worker threads do not inherit contextvars, which carry the tracing span; give each its own copy.
            pending = [
                executor.submit(
                    contextvars.copy_context().run,
                    self._fetch_crossmatch_inputs,
                    query,
                    chunk,
                    radius_deg,
                    bulk=False,
                )
                for chunk in chunks
            ]
            return [row for future in pending for row in future.result()]

    def _fetch_crossmatch_inputs(
        self, query: sql.Composable, record_ids: list[str], radius_deg: float, *, bulk: bool
    ) -> list[dict[str, Any]]:
        with self.with_tx():
            self._storage.exec("SET TRANSACTION READ ONLY")
            if bulk:
                self._storage.exec("SET LOCAL enable_nestloop = off")
            self._storage.exec("SET LOCAL jit = off")
            # RA above 180 deg is valid but makes PostGIS emit a NOTICE per row when casting to geography.
            self._storage.exec("SET LOCAL client_min_messages = warning")
            with self._storage.get_connection().cursor() as cursor:
                cursor.execute(query, {"ids": record_ids, "radius": radius_deg})
                return cursor.fetchall()

    def layer2_pgcs(self, pgcs: list[int]) -> set[int]:
        return crossmatch_data.layer2_pgcs(self._storage, pgcs, read_only=True)
