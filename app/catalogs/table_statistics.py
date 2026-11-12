from dataclasses import dataclass, field

type StatValue = int | float | str | bool


@dataclass
class CatalogProgress:
    structured: int


@dataclass
class ColumnProgress:
    non_null_count: int
    min: StatValue | None = None
    max: StatValue | None = None


@dataclass
class TableProgress:
    total_records: int
    unprocessed: int
    pending_triage: int
    resolved_unsubmitted: int
    submitted: int
    catalogs: dict[str, CatalogProgress]
    columns: dict[str, ColumnProgress] = field(default_factory=dict)
