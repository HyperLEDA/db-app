from typing import Any

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
