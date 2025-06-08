import abc
from collections.abc import Callable
from typing import Any, final

import numpy as np
from astropy import units as u


class ColumnModifier(abc.ABC):
    @abc.abstractmethod
    def apply(self, column: u.Quantity) -> u.Quantity | np.ndarray:
        pass


@final
class AddUnitColumnModifier(ColumnModifier):
    """
    Strips the column from its current unit and returns a column with a new unit attached.
    """

    def __init__(self, unit: str) -> None:
        self.unit = u.Unit(unit)

    def apply(self, column: u.Quantity) -> u.Quantity | np.ndarray:
        unitless_column = column.to_value()
        return unitless_column * self.unit


@final
class MapColumnModifier(ColumnModifier):
    """
    Maps values in the column according to a provided mapping dictionary.
    If a value is not found in the mapping, uses the default value.
    Strips the unit from the input column and returns a dimensionless result.
    """

    def __init__(self, mapping: dict[Any, Any], default: Any) -> None:
        self.mapping = mapping
        self.default = default

    def apply(self, column: u.Quantity) -> u.Quantity | np.ndarray:
        values = column.to_value()
        result = np.full((len(column),), self.default)

        for key, value in self.mapping.items():
            mask = values == key
            result[mask] = value

        return result


@final
class FormatColumnModifier(ColumnModifier):
    """
    Formats values in the column according to a provided Python format string.
    The format string can contain any valid Python format specifier, e.g. '{:.2f}' for float formatting.
    Strips the unit from the input column and returns a dimensionless result.
    """

    def __init__(self, pattern: str) -> None:
        try:
            # Test if the pattern is valid by formatting a dummy value
            pattern.format(0)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid format pattern: {e}") from e

        self.pattern = pattern
        self._format_func: Callable = np.frompyfunc(lambda x: self.pattern.format(x), 1, 1)

    def apply(self, column: u.Quantity) -> u.Quantity | np.ndarray:
        return self._format_func(column.to_value())
