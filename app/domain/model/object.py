import datetime
from dataclasses import dataclass


@dataclass
class ObjectNameInfo:
    name: str
    source_id: int
    modification_time: datetime.datetime


@dataclass
class GetObjectNamesRequest:
    id: int
    page_size: int
    page: int


@dataclass
class GetObjectNamesResponse:
    names: list[ObjectNameInfo]
