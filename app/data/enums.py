from psycopg.types import enum

from app.lib.storage import enums

PG_ENUM_REGISTRY: list[tuple[type[enum.Enum], str]] = [
    (enums.DataType, "common.datatype"),
    (enums.RecordTriageStatus, "layer0.triage_status"),
]
