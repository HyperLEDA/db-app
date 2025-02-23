from collections.abc import Hashable
from typing import Any, final

import astropy
import astropy.constants
import numpy as np

from app.data import model
from app.data.model.interface import CatalogObject
from app.domain.converters import common, errors, interface


@final
class RedshiftConverter(interface.QuantityConverter):
    def __init__(self) -> None:
        self.column_name = None
        self.unit = None

    @staticmethod
    def name() -> str:
        return "redshift"

    def parse_columns(self, columns: list[model.ColumnDescription]) -> None:
        column = common.get_main_column(columns, "src.redshift")

        self.column_name = column.name
        self.unit = column.unit

    def apply(self, data: dict[Hashable, Any]) -> CatalogObject:
        raw_z = data[self.column_name]

        if raw_z is None or np.isnan(raw_z):
            raise errors.ConverterError("Redshift is NaN")

        if self.unit is None:
            z = raw_z * astropy.constants.c
        else:
            z = raw_z * self.unit

        return model.RedshiftCatalogObject(z.value, 0.1)
