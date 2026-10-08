from dataclasses import dataclass

from app.catalogs import layer1
from app.lib.storage import enums


@dataclass
class CrossmatchRecordRow:
    record_id: str
    triage_status: enums.RecordTriageStatus
    candidates: list[int]


@dataclass
class Record:
    id: str
    data: list[layer1.CatalogObject]

    def get[T](self, t: type[T]) -> T | None:
        for obj in self.data:
            if isinstance(obj, t):
                return obj
        return None


@dataclass
class DesignationRecord:
    design: str


@dataclass
class ICRSRecord:
    ra: float
    e_ra: float
    dec: float
    e_dec: float


@dataclass
class RedshiftRecord:
    cz: float
    e_cz: float


@dataclass
class NatureRecord:
    type_name: str
