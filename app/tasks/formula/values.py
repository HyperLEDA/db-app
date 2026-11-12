from collections.abc import Sequence
from dataclasses import dataclass
from typing import final

import numpy as np
from astropy import units as u
from astropy.units.function.core import FunctionUnitBase


@final
@dataclass(frozen=True)
class TextValue:
    data: str
    unit: str = ""

    def __add__(self, other: object) -> str:
        if isinstance(other, TextValue):
            return self.data + other.data
        if isinstance(other, str):
            return self.data + other
        return NotImplemented

    def __radd__(self, other: object) -> str:
        if isinstance(other, str):
            return other + self.data
        return NotImplemented


type Value = u.Quantity | str | TextValue | np.ndarray


def scalar_to_str(value: float | int | np.number) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return str(numeric)


def value_to_str(value: Value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, TextValue):
        return value.data
    if isinstance(value, u.Quantity):
        return _quantity_to_str(value)
    return _array_to_str(value)


def _quantity_to_str(value: u.Quantity) -> str:
    scalar = value.value
    if isinstance(scalar, np.ndarray):
        if scalar.shape != ():
            raise ValueError("expression must evaluate to a scalar value per row")
        return scalar_to_str(scalar.item())
    return scalar_to_str(scalar)


def _array_to_str(value: np.ndarray) -> str:
    if value.shape != ():
        raise ValueError("expression must evaluate to a scalar value per row")
    item = value.item()
    if isinstance(item, str):
        return item
    if isinstance(item, bool) or not isinstance(item, (int, float, np.number)):
        raise ValueError(f"unsupported expression result type: {type(item).__name__}")
    return scalar_to_str(item)


def _is_logarithmic_column_unit(unit: u.UnitBase) -> bool:
    return unit == u.Unit("mag") or unit == u.Unit("dex") or isinstance(unit, FunctionUnitBase)


def column_quantity(value: float | str | Sequence[float] | Sequence[str], unit: str) -> Value:
    if isinstance(value, str):
        return TextValue(value, unit) if unit else value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and all(isinstance(x, str) for x in value):
        return np.asarray(value)
    numeric = np.asarray(value, dtype=float)
    if not unit:
        return numeric * u.Unit("")
    parsed = u.Unit(unit)
    if _is_logarithmic_column_unit(parsed):
        return numeric * u.Unit("")
    return numeric * parsed
