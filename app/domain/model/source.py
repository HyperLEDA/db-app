from dataclasses import dataclass


@dataclass
class CreateSourceRequest:
    bibcode: str | None = None
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None


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
