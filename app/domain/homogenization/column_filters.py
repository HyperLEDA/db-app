from abc import ABC, abstractmethod
from typing import final

from app.data import model


class ColumnFilter(ABC):
    @abstractmethod
    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        pass


@final
class UCDColumnFilter(ColumnFilter):
    def __init__(self, ucd: str):
        self.ucd = ucd

    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        return column.ucd == self.ucd


@final
class ColumnNameColumnFilter(ColumnFilter):
    def __init__(self, column_name: str):
        self.column_name = column_name

    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        return column.name == self.column_name


@final
class AndColumnFilter(ColumnFilter):
    def __init__(self, filters: list[ColumnFilter]):
        self.filters = filters

    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        return all(f.apply(table, column) for f in self.filters)
