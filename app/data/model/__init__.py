import datetime
from dataclasses import dataclass


@dataclass
class Bibliography:
    bibcode: str
    year: int
    author: list[str]
    title: str
    id: int | None = None


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
