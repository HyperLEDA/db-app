from dataclasses import dataclass


@dataclass
class CatalogProgress:
    structured: int


@dataclass
class TableProgress:
    total_records: int
    unprocessed: int
    pending_triage: int
    resolved_unsubmitted: int
    submitted: int
    catalogs: dict[str, CatalogProgress]
