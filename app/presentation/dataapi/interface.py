import abc
from dataclasses import dataclass

from app.presentation.dataapi import model


@dataclass
class QuerySimpleRequest:
    ra: float | None = None
    dec: float | None = None
    radius: float | None = None
    name: str | None = None
    designation: str | None = None
    page_size: int = 25
    page: int = 0


@dataclass
class QuerySimpleResponse:
    objects: list[model.PGCObject]


class Actions(abc.ABC):
    @abc.abstractmethod
    def query_simple(self, query: QuerySimpleRequest) -> QuerySimpleResponse:
        pass
