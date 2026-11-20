import json
from typing import Any

from psycopg import sql

from app.lib.storage import enums, postgres

_UPSERT = (
    "INSERT INTO layer0.crossmatch (record_id, triage_status, metadata) "
    "VALUES (%s, %s, %s) "
    "ON CONFLICT (record_id) DO UPDATE SET "
    "triage_status = EXCLUDED.triage_status, metadata = EXCLUDED.metadata"
)


def candidates_to_metadata(candidates: list[int]) -> dict[str, Any]:
    if not candidates:
        return {}
    return {"pgc": candidates[0]} if len(candidates) == 1 else {"possible_matches": candidates}


def write_crossmatch_rows(
    storage: postgres.PgStorage,
    rows: list[tuple[str, enums.RecordTriageStatus, list[int]]],
) -> None:
    payload = [(rid, triage.value, json.dumps(candidates_to_metadata(cands))) for rid, triage, cands in rows]
    with storage.get_connection().cursor() as cursor:
        cursor.executemany(_UPSERT, payload)


def fetch_claimed_pgcs(
    storage: postgres.PgStorage,
    table_name: str,
    column: str,
    record_ids: list[str],
    *,
    read_only: bool = False,
) -> dict[str, int | None]:
    if not record_ids:
        return {}
    query = sql.SQL(
        "SELECT hyperleda_internal_id, {col} FROM rawdata.{table} WHERE hyperleda_internal_id = ANY(%s)"
    ).format(col=sql.Identifier(column), table=sql.Identifier(table_name))
    return {
        str(row["hyperleda_internal_id"]): int(row[column]) if row[column] is not None else None
        for row in storage.query(query, params=[record_ids], read_only=read_only)
    }


def layer2_pgcs(storage: postgres.PgStorage, pgcs: list[int], *, read_only: bool = False) -> set[int]:
    if not pgcs:
        return set()
    return {
        int(row["pgc"])
        for row in storage.query(
            "SELECT pgc FROM layer2.objects WHERE pgc = ANY(%s)", params=[pgcs], read_only=read_only
        )
    }


def pgcs_by_designation(
    storage: postgres.PgStorage,
    designations: list[str],
    *,
    read_only: bool = False,
) -> dict[str, list[int]]:
    if not designations:
        return {}
    grouped: dict[str, set[int]] = {}
    for query in (
        "SELECT name AS design, pgc FROM layer2.objects WHERE name = ANY(%s)",
        "SELECT design, pgc FROM layer2.designations WHERE design = ANY(%s)",
    ):
        for row in storage.query(query, params=[designations], read_only=read_only):
            grouped.setdefault(str(row["design"]), set()).add(int(row["pgc"]))
    return {design: sorted(grouped.get(design, set())) for design in designations}
