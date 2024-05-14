from dataclasses import dataclass


@dataclass
class CreateSourceRequest:
    bibcode: str
    title: str | None
    authors: list[str] | None
    year: int | None


@dataclass
class CreateSourceResponse:
    id: int


@dataclass
class GetSourceRequest:
    id: int


@dataclass
class GetSourceResponse:
    bibcode: str
    title: str
    authors: list[str]
    year: int


@dataclass
class GetSourceListRequest:
    title: str
    page_size: int
    page: int


@dataclass
class GetSourceListResponse:
    sources: list[GetSourceResponse]
