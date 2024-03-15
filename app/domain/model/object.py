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
class GetObjectRequest:
    id: int


@dataclass
class GetObjectResponse:
    object: ObjectInfo


@dataclass
class SearchObjectsRequest:
    ra: float
    dec: float
    radius: float
    type: str
    page_size: int
    page: int


@dataclass
class SearchObjectsResponse:
    objects: list[ObjectInfo]
