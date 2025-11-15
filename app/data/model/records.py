from dataclasses import dataclass

from app.data.model import interface


@dataclass
class CIResultObjectNew:
    pass


@dataclass
class CIResultObjectExisting:
    pgc: int


@dataclass
class CIResultObjectCollision:
    pgcs: set[int]


CIResult = CIResultObjectNew | CIResultObjectExisting | CIResultObjectCollision


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
class RecordCrossmatch:
    record: Record
    processing_result: CIResult


@dataclass
class RecordWithPGC:
    pgc: int
    record: Record
