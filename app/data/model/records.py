from dataclasses import dataclass

from app.data.model import interface
from app.lib.storage import enums


@dataclass
class CrossmatchRecordRow:
    record_id: str
    triage_status: enums.RecordTriageStatus
    candidates: list[int]


@dataclass
class Record:
    id: str
    data: list[interface.CatalogObject]

    def get[T](self, t: type[T]) -> T | None:
        for obj in self.data:
            if isinstance(obj, t):
                return obj

        return None


@dataclass
class NatureRecord:
    pgc: int
    record_id: str
    type_name: str


@dataclass
class ICRSRecord:
    pgc: int
    record_id: str
    ra: float
    e_ra: float
    dec: float
    e_dec: float


@dataclass
class RedshiftRecord:
    pgc: int
    record_id: str
    cz: float
    e_cz: float


@dataclass
class DesignationRecord:
    pgc: int
    record_id: str
    design: str
