import abc
from typing import final

from astropy import units as u


class ColumnModifier(abc.ABC):
    @abc.abstractmethod
    def apply(self, column: u.Quantity) -> u.Quantity:
        pass


@final
class AddUnitColumnModifier(ColumnModifier):
    """
    Strips the column from its current unit and returns a column with a new unit attached.
    """

    def __init__(self, unit: str) -> None:
        self.unit = u.Unit(unit)

    def apply(self, column: u.Quantity) -> u.Quantity:
        unitless_column = column.to_value()

        return unitless_column * self.unit
