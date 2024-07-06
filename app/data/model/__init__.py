import datetime
from dataclasses import dataclass

from app.data.model.common import Bibliography
from app.data.model.layer0 import ColumnDescription, Layer0Creation, Layer0RawData
from app.data.model.task import Task
from app.lib.storage.enums import TaskStatus

__all__ = [
    "Bibliography",
    "ColumnDescription",
    "Layer0Creation",
    "Layer0RawData",
    "Task",
    "TaskStatus",
]


@dataclass
class PGCObject:
    id: int


@dataclass
class Designation:
    design: str
    bib: int
    modification_time: datetime.datetime | None = None
    pgc: int | None = None


@dataclass
class CoordinateData:
    pgc: int
    ra: float
    dec: float
    bib: int
    id: int | None = None
    modification_time: datetime.datetime | None = None
