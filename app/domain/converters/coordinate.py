from typing import final

import pandas
from astropy import coordinates
from astropy import units as u
from numpy.typing import NDArray

from app import entities
from app.domain.converters import common, errors, interface


@final
class CoordinateConverter(interface.QuantityConverter):
    def __init__(self, ucd: str) -> None:
        self.ucd = ucd
        self.column = None

    def parse_columns(self, columns: list[entities.ColumnDescription]) -> None:
        column = common.get_main_column(columns, self.ucd)

        if column.unit is None:
            raise errors.ConverterError(f"Column has correct ucd ({self.ucd}) but has no units")

        try:
            _ = coordinates.Angle(1 * column.unit)
        except u.UnitsError:
            raise errors.ConverterError(f"Column {column.name} does not have a valid angular unit") from None

        self.column = column

    def convert(self, data: pandas.DataFrame) -> NDArray:
        if self.column is None:
            raise errors.ConverterError("unknown rules for coordinate specification")

        return coordinates.Angle(data[self.column.name].to_numpy() * self.column.unit)
