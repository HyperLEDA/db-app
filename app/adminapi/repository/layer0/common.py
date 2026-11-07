from collections.abc import Generator, Sequence
from contextlib import contextmanager
from typing import Any

from app.lib.storage import postgres

RAWDATA_SCHEMA = "rawdata"
INTERNAL_ID_COLUMN_NAME = "hyperleda_internal_id"


def metadata_to_candidates(metadata: dict[str, Any] | None) -> list[int]:
    if metadata is None:
        return []
    if "pgc" in metadata and metadata["pgc"] is not None:
        return [int(metadata["pgc"])]
    if "possible_matches" in metadata and metadata["possible_matches"] is not None:
        return [int(p) for p in metadata["possible_matches"]]
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
