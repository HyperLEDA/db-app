from abc import ABC, abstractmethod
from typing import Any, final

from app.data import model


class ColumnFilter(ABC):
    @abstractmethod
    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        pass


def parse_filters(filters: dict[str, Any]) -> ColumnFilter:
    parsed_filters = []

    for f, value in filters.items():
        if f == "ucd":
            parsed_filters.append(UCDColumnFilter(value))
        elif f == "column_name":
            parsed_filters.append(ColumnNameColumnFilter(value))
        elif f == "table_name":
            parsed_filters.append(TableNameColumnFilter(value))
        elif f == "datatype_oneof":
            parsed_filters.append(DataTypeOneOfFilter(value))
        else:
            raise ValueError(f"Unknown filter: {f}")

    return AndColumnFilter(parsed_filters)


@final
class UCDColumnFilter(ColumnFilter):
    def __init__(self, ucd: str):
        self.ucd = ucd

    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        return column.ucd == self.ucd


@final
class DataTypeOneOfFilter(ColumnFilter):
    def __init__(self, datatypes: list[str]) -> None:
        self.datatypes = datatypes

    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        return column.data_type in self.datatypes


@final
class TableNameColumnFilter(ColumnFilter):
    def __init__(self, table_name: str):
        self.table_name = table_name

    def apply(self, table: model.Layer0TableMeta, column: model.ColumnDescription) -> bool:
        return table.table_name == self.table_name


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
