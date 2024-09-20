from typing import Any, Hashable, final

from astropy import coordinates
from astropy import units as u

from app import entities
from app.domain.converters import common, errors, interface


@final
class ICRSConverter(interface.QuantityConverter):
    def __init__(self) -> None:
        self.ra_column = None
        self.dec_column = None

    def name(self) -> str:
        return "ICRS"

    def parse_columns(self, columns: list[entities.ColumnDescription]) -> None:
        ra_column = common.get_main_column(columns, "pos.eq.ra")
        dec_column = common.get_main_column(columns, "pos.eq.dec")

        for name, column in zip(["RA", "dec"], [ra_column, dec_column]):
            if column.unit is None:
                raise errors.ConverterError(f"Column '{column.name}' (for {name}) has no units")
            try:
                _ = coordinates.Angle(1 * column.unit)
            except u.UnitsError:
                raise errors.ConverterError(f"Column {column.name} does not have a valid angular unit") from None

        self.ra_column = ra_column
        self.dec_column = dec_column

    def apply(self, object_info: entities.ObjectInfo, data: dict[Hashable, Any]) -> entities.ObjectInfo:
        if self.ra_column is None or self.dec_column is None:
            raise errors.ConverterError("unknown rules for coordinate specification")

        object_info.coordinates = coordinates.ICRS(
            ra=data[self.ra_column.name] * self.ra_column.unit,
            dec=data[self.dec_column.name] * self.dec_column.unit,
        )

        return object_info
