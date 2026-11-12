from typing import Any

import structlog

from app.catalogs.layer0 import INTERNAL_ID_COLUMN_NAME as INTERNAL_ID_COLUMN_NAME
from app.catalogs.layer0 import RAWDATA_SCHEMA as RAWDATA_SCHEMA
from app.catalogs.layer0 import rawdata_table as rawdata_table

log: structlog.stdlib.BoundLogger = structlog.get_logger()


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
