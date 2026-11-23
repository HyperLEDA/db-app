import json
from typing import Any

from app.lib.storage import enums, postgres

_UPSERT = """
    INSERT INTO layer0.crossmatch (record_id, triage_status, metadata)
    SELECT * FROM unnest(%s::text[], %s::layer0.triage_status[], %s::json[]) ORDER BY 1
    ON CONFLICT (record_id) DO UPDATE SET triage_status = EXCLUDED.triage_status, metadata = EXCLUDED.metadata
"""


def candidates_to_metadata(candidates: list[int]) -> dict[str, Any]:
    if not candidates:
        return {}
    return {"pgc": candidates[0]} if len(candidates) == 1 else {"possible_matches": candidates}


def write_crossmatch_rows(
    storage: postgres.PgStorage,
    rows: list[tuple[str, enums.RecordTriageStatus, list[int]]],
) -> None:
    # A single INSERT cannot touch the same row twice, so keep the last write per record like row-by-row upserts did.
    latest = {rid: (triage, cands) for rid, triage, cands in rows}
    storage.exec(
        _UPSERT,
        params=[
            list(latest),
            [triage.value for triage, _ in latest.values()],
            [json.dumps(candidates_to_metadata(cands)) for _, cands in latest.values()],
        ],
    )


def layer2_pgcs(storage: postgres.PgStorage, pgcs: list[int], *, read_only: bool = False) -> set[int]:
    if not pgcs:
        return set()
    return {
        int(row["pgc"])
        for row in storage.query(
            "SELECT pgc FROM layer2.objects WHERE pgc = ANY(%s)", params=[pgcs], read_only=read_only
        )
    }
