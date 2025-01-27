import abc
from dataclasses import dataclass

from app.presentation.dataapi import model


@dataclass
class QuerySimpleRequest:
    ra: float
    dec: float
    radius: float
    name: str
    designation: str
    page_size: int
    page: int


@dataclass
class QuerySimpleResponse:
    objects: list[model.PGCObject]


@dataclass
class GetObjectRequest:
    pgc: int


@dataclass
class GetObjectResponse:
    object: model.PGCObject


class Actions(abc.ABC):
    @abc.abstractmethod
    def query_simple(self, query: QuerySimpleRequest) -> QuerySimpleResponse:
        pass

    @abc.abstractmethod
    def get_object(self, query: GetObjectRequest) -> GetObjectResponse:
        pass
