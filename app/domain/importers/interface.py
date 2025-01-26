import abc
import datetime
from typing import Any

from app.data import model

pgc = int
UnaggregatedInfo = dict[model.RawCatalog, list[Any]]
ObjectInfo = dict[model.RawCatalog, Any]


class Importer(abc.ABC):
    @abc.abstractmethod
    def collect(self, dt: datetime.datetime) -> dict[pgc, UnaggregatedInfo]:
        pass

    @abc.abstractmethod
    def aggregate(self, unaggregated_info: UnaggregatedInfo) -> ObjectInfo:
        pass

    @abc.abstractmethod
    def write(self, objects: dict[pgc, ObjectInfo]) -> None:
        pass
