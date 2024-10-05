from dataclasses import dataclass

from app.lib.storage import enums


@dataclass
class TableStatusStatsRequest:
    table_id: int


@dataclass
class TableStatusStatsResponse:
    processing: dict[enums.ObjectProcessingStatus, int]


@dataclass
class SetTableStatusOverrides:
    id: str
    pgc: int | None = None


@dataclass
class SetTableStatusRequest:
    table_id: int
    overrides: list[SetTableStatusOverrides]
    batch_size: int = 100


@dataclass
class SetTableStatusResponse:
    pass
