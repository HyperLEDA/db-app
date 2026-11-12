from dataclasses import dataclass, field


@dataclass
class CatalogProgress:
    structured: int


@dataclass
class ColumnProgress:
    non_null_count: int


@dataclass
class TableProgress:
    total_records: int
    unprocessed: int
    pending_triage: int
    resolved_unsubmitted: int
    submitted: int
    catalogs: dict[str, CatalogProgress]
    columns: dict[str, ColumnProgress] = field(default_factory=dict)
