import abc
from dataclasses import dataclass

from app.presentation.dataapi import model


@dataclass
class QuerySimpleRequest:
    pgcs: list[int] | None = None
    ra: float | None = None
    dec: float | None = None
    radius: float | None = None
    name: str | None = None
    cz: float | None = None
    cz_err_percent: float | None = None
    page_size: int = 25
    page: int = 0


@dataclass
class QuerySimpleResponse:
    objects: list[model.PGCObject]
    schema: model.Schema


@dataclass
class QueryRequest:
    q: str
    page_size: int = 10
    page: int = 0


@dataclass
class QueryResponse:
    objects: list[model.PGCObject]


@dataclass
class FITSRequest:
    pgcs: list[int] | None = None
    ra: float | None = None
    dec: float | None = None
    radius: float | None = None
    name: str | None = None
    cz: float | None = None
    cz_err_percent: float | None = None
    page_size: int = 25
    page: int = 0


class Actions(abc.ABC):
    @abc.abstractmethod
    def query_simple(self, query: QuerySimpleRequest) -> QuerySimpleResponse:
        pass

    @abc.abstractmethod
    def query(self, query: QueryRequest) -> QueryResponse:
        pass

    @abc.abstractmethod
    def query_fits(self, query: FITSRequest) -> bytes:
        pass
