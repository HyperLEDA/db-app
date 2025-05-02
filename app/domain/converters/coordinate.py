from collections.abc import Hashable
from dataclasses import dataclass
from typing import Any, final

from astropy import coordinates
from astropy import units as u

from app.data import model
from app.domain.converters import common, errors, interface


@dataclass
class ColumnInfo:
    name: str
    unit: u.Unit

    def apply(self, data: dict[Hashable, Any]) -> u.Quantity:
        return coordinates.Angle(data[self.name], unit=self.unit)

    @staticmethod
    def parse(column: model.ColumnDescription) -> "ColumnInfo":
        name = column.name

        if column.unit is None:
            raise errors.ConverterError(f"Column {column.name} does not have a unit")

        try:
            _ = coordinates.Angle(1 * column.unit)
        except u.UnitsError:
            raise errors.ConverterError(
                f"Column {column.name} (for {name}) does not have a valid angular unit"
            ) from None

        return ColumnInfo(name, column.unit)


@final
class ICRSConverter(interface.QuantityConverter):
    def __init__(self) -> None:
        self.ra_column = None
        self.dec_column = None

    @staticmethod
    def name() -> str:
        return "ICRS"

    def parse_columns(self, columns: list[model.ColumnDescription]) -> None:
        self.ra_column = ColumnInfo.parse(common.get_main_column(columns, "pos.eq.ra"))
        self.dec_column = ColumnInfo.parse(common.get_main_column(columns, "pos.eq.dec"))

    def apply(self, data: dict[Hashable, Any]) -> model.CatalogObject:
        if self.ra_column is None or self.dec_column is None:
            raise errors.ConverterError("unknown rules for coordinate specification")

        coords = coordinates.ICRS(ra=self.ra_column.apply(data), dec=self.dec_column.apply(data))
        ra = coords.ra.deg
        dec = coords.dec.deg

        return model.ICRSCatalogObject(ra=ra, e_ra=0.01, dec=dec, e_dec=0.01)
