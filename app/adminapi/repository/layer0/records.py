import json
from typing import Any

from app.adminapi.repository.common import touch_pgcs
from app.adminapi.repository.layer0.common import rawdata_table
from app.lib.storage import enums, postgres


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

        with rawdata_table(self._storage, table_name=table_name) as table_ids:
            table_id = table_ids[0]
            query = (
                "INSERT INTO layer0.records (id, table_id) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET table_id = EXCLUDED.table_id"
            )
            rows = [[record_id, table_id] for record_id in record_ids]
            self._storage.execute_batch(query, rows)

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
            with rawdata_table(self._storage, record_ids=[record_id for record_id, _, _ in rows]):
                with self._storage.get_connection().cursor() as cursor:
                    cursor.executemany(query, db_rows)

    def assign_record_pgcs(self, record_ids: list[str]) -> None:
        if not record_ids:
            return

        with self.with_tx():
            with self._storage.get_connection().cursor() as cur:
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
                minted = self._mint_pgc_ids(len(new_rows))
                for row, pgc_id in zip(new_rows, minted, strict=True):
                    pgcs_to_insert[row["record_id"]] = pgc_id

            if pgcs_to_insert:
                with rawdata_table(self._storage, record_ids=list(pgcs_to_insert.keys())):
                    update_query = (
                        "UPDATE layer0.records SET pgc = v.pgc "
                        "FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
                        "WHERE layer0.records.id = v.record_id AND layer0.records.pgc IS NULL"
                    )
                    rows = [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()]
                    self._storage.execute_batch(update_query, rows)
                    touch_pgcs(self._storage, list(set(pgcs_to_insert.values())))

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        pgcs_to_insert: dict[str, int] = {}

        new_records = [record_id for record_id, pgc in pgcs.items() if pgc is None]
        if new_records:
            shared_pgc = self._mint_pgc_ids(1)[0]
            for record_id in new_records:
                pgcs_to_insert[record_id] = shared_pgc

        for record_id, pgc in pgcs.items():
            if pgc is not None:
                pgcs_to_insert[record_id] = pgc

        if pgcs_to_insert:
            with rawdata_table(self._storage, record_ids=list(pgcs_to_insert.keys())):
                previous_rows = self._storage.query(
                    "SELECT pgc FROM layer0.records WHERE id = ANY(%s) AND pgc IS NOT NULL",
                    params=[list(pgcs_to_insert.keys())],
                )
                previous_pgcs = {int(row["pgc"]) for row in previous_rows}
                update_query = (
                    "UPDATE layer0.records SET pgc = v.pgc FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
                    "WHERE layer0.records.id = v.record_id"
                )
                rows = [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()]
                self._storage.execute_batch(update_query, rows)
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
