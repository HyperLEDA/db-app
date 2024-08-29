from astropy import coordinates
from astropy import units as u
from numpy.typing import NDArray

from app import entities
from app.domain.converters import errors, interface


class CoordinateConverter(interface.QuantityConverter):
    def __init__(self, column_info: entities.ColumnDescription) -> None:
        if column_info.unit is None:
            raise errors.ConverterError(f"Column {column_info.name} does not have a valid angular unit") from None

        try:
            _ = coordinates.Angle(1 * column_info.unit)
        except u.UnitsError:
            raise errors.ConverterError(f"Column {column_info.name} does not have a valid angular unit") from None

        self.unit = column_info.unit

    def convert(self, columns: list[NDArray]) -> NDArray:
        if len(columns) != 1:
            raise errors.ConverterError("Wrong number of columns to convert from")

        return coordinates.Angle(columns[0] * self.unit)
