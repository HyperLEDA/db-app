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


# TODO: remove
@dataclass
class Layer1Observation:
    object_id: str
    catalog_object: interface.CatalogObject


@dataclass
class RecordInfo:
    id: str
    data: list[interface.CatalogObject]

    def get[T](self, t: type[T]) -> T | None:
        for obj in self.data:
            if isinstance(obj, t):
                return obj

        return None


@dataclass
class RecordCrossmatch:
    record: RecordInfo
    processing_result: CIResult


# TODO: use RecordInfo directly
@dataclass
class Layer1PGCObservation:
    pgc: int
    observation: Layer1Observation
