import abc
from typing import final

from app.data import model


class TableFilter(abc.ABC):
    @abc.abstractmethod
    def apply(self, table: model.Layer0TableMeta) -> bool:
        pass


@final
class TableNameFilter(TableFilter):
    def __init__(self, table_name: str):
        self.table_name = table_name

    def apply(self, table: model.Layer0TableMeta) -> bool:
        return table.table_name == self.table_name


@final
class AndTableFilter(TableFilter):
    def __init__(self, filters: list[TableFilter]):
        self.filters = filters

    def apply(self, table: model.Layer0TableMeta) -> bool:
        return all(f.apply(table) for f in self.filters)
