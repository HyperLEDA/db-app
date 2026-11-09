from collections.abc import Generator, Sequence
from contextlib import contextmanager
from typing import Any

import structlog

from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()

RAWDATA_SCHEMA = "rawdata"
INTERNAL_ID_COLUMN_NAME = "hyperleda_internal_id"


def metadata_to_candidates(metadata: dict[str, Any] | None) -> list[int]:
    if not isinstance(metadata, dict):
        return []
    if "pgc" in metadata and metadata["pgc"] is not None:
        return _candidate_ids([metadata["pgc"]])
    if "possible_matches" in metadata and metadata["possible_matches"] is not None:
        return _candidate_ids(metadata["possible_matches"])
    return []


def _candidate_ids(values: Any) -> list[int]:
    try:
        return [int(value) for value in values]
    except (TypeError, ValueError) as exc:
        log.error("Failed to read crossmatch candidates", exc_info=exc)
        return []


@contextmanager
def rawdata_table(
    storage: postgres.PgStorage,
    *,
    table_name: str | None = None,
    record_ids: Sequence[str] | None = None,
) -> Generator[list[int]]:
    if (table_name is None) == (record_ids is None):
        raise ValueError("provide exactly one of table_name or record_ids")

    if table_name is not None:
        try:
            row = storage.query_one(
                "SELECT id FROM layer0.tables WHERE table_name = %s",
                params=[table_name],
            )
        except RuntimeError as e:
            raise RuntimeError(f"table {table_name!r} is not in layer0.tables") from e
        table_ids = [int(row["id"])]
    elif not record_ids:
        table_ids = []
    else:
        rows = storage.query(
            "SELECT DISTINCT table_id FROM layer0.records WHERE id = ANY(%s)",
            params=[list(record_ids)],
        )
        table_ids = [int(row["table_id"]) for row in rows]

    yield table_ids
    if table_ids:
        storage.exec(
            "UPDATE layer0.tables SET modification_dt = now() WHERE id = ANY(%s)",
            params=[table_ids],
        )
