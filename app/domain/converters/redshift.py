from collections.abc import Hashable
from typing import Any

from app import entities
from app.domain.converters import common, interface


class RedshiftConverter(interface.QuantityConverter):
    def __init__(self) -> None:
        self.column = None

    def name(self) -> str:
        return "Redshift"

    def parse_columns(self, columns: list[entities.ColumnDescription]) -> None:
        self.column = common.get_main_column(columns, "src.redshift")

    def apply(self, object_info: entities.ObjectInfo, data: dict[Hashable, Any]) -> entities.ObjectInfo:
        return object_info
