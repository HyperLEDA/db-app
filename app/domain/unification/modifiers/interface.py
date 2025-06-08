import abc
from collections.abc import Callable, Sequence
from typing import Any, final

import numpy as np
from astropy import units as u


class ColumnModifier(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def name(cls) -> str:
        pass

    @abc.abstractmethod
    def apply(self, column: u.Quantity | Sequence) -> u.Quantity | np.ndarray:
        pass


@final
class AddUnitColumnModifier(ColumnModifier):
    """
    Strips the column from its current unit and returns a column with a new unit attached.
    """

    @classmethod
    def name(cls) -> str:
        return "add_unit"

    def __init__(self, unit: str) -> None:
        self.unit = u.Unit(unit)

    def apply(self, column: u.Quantity | Sequence) -> u.Quantity | np.ndarray:
        values = column

        if isinstance(column, u.Quantity):
            values = column.to_value()

        return values * self.unit


@final
class MapColumnModifier(ColumnModifier):
    """
    Maps values in the column according to a provided mapping dictionary.
    If a value is not found in the mapping, uses the default value.
    Strips the unit from the input column and returns a dimensionless result.
    """

    @classmethod
    def name(cls) -> str:
        return "map"

    def __init__(self, mapping: dict[Any, Any], default: Any) -> None:
        self.mapping = mapping
        self.default = default

    def apply(self, column: u.Quantity | Sequence) -> u.Quantity | np.ndarray:
        values = column

        if isinstance(column, u.Quantity):
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

    @classmethod
    def name(cls) -> str:
        return "format"

    def __init__(self, pattern: str) -> None:
        try:
            # Test if the pattern is valid by formatting a dummy value
            pattern.format(0)
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid format pattern: {e}") from e

        self.pattern = pattern
        self._format_func: Callable = np.frompyfunc(lambda x: self.pattern.format(x), 1, 1)

    def apply(self, column: u.Quantity | Sequence) -> u.Quantity | np.ndarray:
        values = column

        if isinstance(column, u.Quantity):
            values = column.to_value()

        return self._format_func(values)
