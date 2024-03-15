from dataclasses import dataclass
from typing import Any


@dataclass
class CreateSourceRequest:
    type: str
    metadata: dict


@dataclass
class CreateSourceResponse:
    id: int


@dataclass
class GetSourceRequest:
    id: int


@dataclass
class GetSourceResponse:
    type: str
    metadata: dict[str, Any]


@dataclass
class GetSourceListRequest:
    type: str
    page_size: int
    page: int


@dataclass
class GetSourceListResponse:
    sources: list[GetSourceResponse]
