from dataclasses import dataclass

from app.lib.storage import enums


@dataclass
class TableStatusStatsRequest:
    table_id: int


@dataclass
class TableStatusStatsResponse:
    processing: dict[enums.ObjectProcessingStatus, int]
