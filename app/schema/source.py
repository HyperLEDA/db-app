from dataclasses import dataclass


@dataclass
class CreateSourceRequest:
    title: str
    authors: list[str]
    year: int


@dataclass
class CreateSourceResponse:
    code: str


@dataclass
class GetSourceRequest:
    id: int


@dataclass
class GetSourceResponse:
    code: str
    title: str
    authors: list[str]
    year: int
