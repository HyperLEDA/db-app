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
class StructuredData[T]:
    pgc: int
    record_id: str
    data: T


# Record classes below represent how data for each particular record is written
# and read directly to and from the tables. Most likely they will correspond
# to actual columns for tables. However, this may no necessarily be true for
# catalogs which have more than one line per record.


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
