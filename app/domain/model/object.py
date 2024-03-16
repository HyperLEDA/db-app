import datetime
from dataclasses import dataclass


@dataclass
class CoordsInfo:
    ra: float
    dec: float


@dataclass
class PositionInfo:
    coordinate_system: str
    epoch: str
    coords: CoordsInfo


@dataclass
class ObjectInfo:
    name: str
    type: str
    position: PositionInfo


@dataclass
class ObjectNameInfo:
    name: str
    source_id: int
    modification_time: datetime.datetime


@dataclass
class CreateObjectBatchRequest:
    source_id: int
    objects: list[ObjectInfo]


@dataclass
class CreateObjectBatchResponse:
    ids: list[int]


@dataclass
class CreateObjectRequest:
    source_id: int
    object: ObjectInfo


@dataclass
class CreateObjectResponse:
    id: int


@dataclass
class GetObjectNamesRequest:
    id: int
    page_size: int
    page: int


@dataclass
class GetObjectNamesResponse:
    names: list[ObjectNameInfo]
