import functools
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import final

import numpy as np
from astropy import coordinates
from astropy import units as u

from app.tasks.formula import values


@final
@dataclass(frozen=True)
class FunctionDef:
    name: str
    detail: str
    impl: object | None = None
    placeholder: str = "${1:x}"

    @property
    def signature(self) -> str:
        args = re.sub(r"\$\{\d+:([^}]+)\}", r"\1", self.placeholder)
        return f"{self.name}({args})"


def _formula_str(value: values.Value) -> str | np.ndarray:
    if isinstance(value, values.TextValue):
        return value.data
    if isinstance(value, str):
        return value
    if isinstance(value, u.Quantity):
        scalar = value.value
        if isinstance(scalar, np.ndarray):
            return np.asarray([values.scalar_to_str(item) for item in scalar])
        return values.scalar_to_str(scalar)
    if value.dtype.kind in "US":
        return value
    return np.asarray([values.scalar_to_str(item) for item in value])


def _to_deg(value: object) -> u.Quantity:
    if isinstance(value, values.TextValue):
        angle = coordinates.Angle(value.data, unit=u.Unit(value.unit)) if value.unit else coordinates.Angle(value.data)
        return angle.to(u.Unit("deg"))
    if isinstance(value, str):
        return coordinates.Angle(value).to(u.Unit("deg"))
    if isinstance(value, u.Quantity):
        return value.to(u.Unit("deg"))
    if isinstance(value, np.ndarray):
        return u.Quantity([_to_deg(item).value for item in value], unit=u.Unit("deg"))
    raise TypeError(f"to_deg() expected angle or coordinate string, got {type(value).__name__}")


def _unit(name: object) -> u.Quantity:
    if not isinstance(name, str):
        raise TypeError(f"unit() expected a unit name string, got {type(name).__name__}")
    return 1 * u.Unit(name)


def _to_quantity(value: object) -> u.Quantity:
    if isinstance(value, u.Quantity):
        return value
    return np.asarray(value, dtype=float) * u.Unit("")


def _math(fn: Callable[..., u.Quantity]) -> Callable[..., u.Quantity]:
    def impl(*args: object) -> u.Quantity:
        return fn(*(_to_quantity(arg) for arg in args))

    return impl


def _as_angle(value: object, default_unit: u.UnitBase) -> u.Quantity:
    if isinstance(value, u.Quantity):
        if value.unit.is_equivalent(u.Unit("rad")):
            return value
        if value.unit.is_equivalent(u.Unit("")):
            return value.to_value(u.Unit("")) * default_unit
        raise TypeError(f"expected an angle or dimensionless value, got unit {value.unit}")
    return np.asarray(value, dtype=float) * default_unit


def _deg2rad(value: object) -> u.Quantity:
    return _as_angle(value, u.Unit("deg")).to(u.Unit("rad"))


def _rad2deg(value: object) -> u.Quantity:
    return _as_angle(value, u.Unit("rad")).to(u.Unit("deg"))


def _wrap360(value: object) -> u.Quantity:
    return _as_angle(value, u.Unit("deg")).to(u.Unit("deg")) % (360 * u.Unit("deg"))


def _extremum(fn: Callable[..., u.Quantity]) -> Callable[[object, object], u.Quantity]:
    def impl(left: object, right: object) -> u.Quantity:
        left_q = left if isinstance(left, u.Quantity) else _to_quantity(left)
        right_q = right if isinstance(right, u.Quantity) else _to_quantity(right)
        aligned = right_q.to(left_q.unit)
        return fn(left_q, aligned)

    return impl


def _mask(cond: object) -> np.ndarray:
    if isinstance(cond, u.Quantity):
        return np.asarray(cond.value)
    return np.asarray(cond)


def _where(cond: object, then: object, otherwise: object) -> object:
    mask = _mask(cond)
    if mask.shape == ():
        return then if bool(mask) else otherwise
    if isinstance(then, u.Quantity) or isinstance(otherwise, u.Quantity):
        then_q = then if isinstance(then, u.Quantity) else _to_quantity(then)
        else_q = otherwise if isinstance(otherwise, u.Quantity) else _to_quantity(otherwise)
        aligned = else_q.to(then_q.unit)
        return np.where(mask, np.asarray(then_q.value), np.asarray(aligned.value)) * then_q.unit
    then_v = then.data if isinstance(then, values.TextValue) else then
    else_v = otherwise.data if isinstance(otherwise, values.TextValue) else otherwise
    return np.where(mask, np.asarray(then_v), np.asarray(else_v))


def _raw(value: object) -> object:
    if isinstance(value, values.TextValue):
        return value.data
    if isinstance(value, u.Quantity):
        return value.value
    return value


def _int(value: object) -> np.ndarray:
    return np.asarray(_to_quantity(value).to_value(u.Unit("")), dtype=int)


def _count(value: object) -> u.Quantity:
    return np.asarray(value, dtype=float) * u.Unit("")


def _logical(fn: Callable[[object, object], np.ndarray]) -> Callable[..., np.ndarray]:
    def impl(first: object, *rest: object) -> np.ndarray:
        return functools.reduce(fn, (_mask(arg) for arg in rest), _mask(first))

    return impl


def _not(cond: object) -> np.ndarray:
    return np.logical_not(_mask(cond))


def _select(*args: object) -> object:
    if len(args) < 3 or len(args) % 2 == 0:
        raise TypeError("select() takes condition/value pairs followed by a default value")
    conds = [_mask(cond) for cond in args[:-1:2]]
    choices = list(args[1:-1:2]) + [args[-1]]
    raw = [np.asarray(_raw(choice)) for choice in choices]
    if any(item.dtype.kind in "US" for item in raw):
        return np.select(conds, raw[:-1], default=raw[-1])
    quantities = [_to_quantity(choice) for choice in choices]
    unit = next((choice.unit for choice in choices if isinstance(choice, u.Quantity)), u.Unit(""))
    aligned = [np.asarray(quantity.to_value(unit)) for quantity in quantities]
    return np.select(conds, aligned[:-1], default=aligned[-1]) * unit


def _isin(x: object, *options: object) -> np.ndarray:
    if isinstance(x, u.Quantity):
        pool = [np.ravel(_to_quantity(option).to_value(x.unit)) for option in options]
    else:
        pool = [np.ravel(np.asarray(_raw(option))) for option in options]
    return np.isin(_raw(x), np.concatenate(pool))


def _string(fn: Callable[..., object], *, numeric_args: tuple[int, ...] = ()) -> Callable[..., object]:
    def impl(text: object, *args: object) -> object:
        converted = [_int(arg) if i in numeric_args else _formula_str(arg) for i, arg in enumerate(args)]
        return fn(_formula_str(text), *converted)

    return impl


def _string_count(fn: Callable[..., object], *, numeric_args: tuple[int, ...] = ()) -> Callable[..., u.Quantity]:
    inner = _string(fn, numeric_args=numeric_args)

    def impl(text: object, *args: object) -> u.Quantity:
        return _count(inner(text, *args))

    return impl


def _contains(text: str | np.ndarray, sub: str | np.ndarray) -> np.ndarray:
    return np.strings.find(text, sub) >= 0


def _num(text: object) -> u.Quantity:
    return np.asarray(_formula_str(text), dtype=float) * u.Unit("")


def _round(x: object, ndigits: object) -> u.Quantity:
    return np.round(_to_quantity(x), int(_int(ndigits)))


COL_FUNCTION = FunctionDef("col", "Rawdata column", placeholder='"${1:name}"')

FUNCTIONS: tuple[FunctionDef, ...] = (
    FunctionDef("sin", "Sine (argument must be an angle)", np.sin),
    FunctionDef("cos", "Cosine (argument must be an angle)", np.cos),
    FunctionDef("tan", "Tangent (argument must be an angle)", np.tan),
    FunctionDef("asin", "Arcsine (returns radians)", _math(np.arcsin)),
    FunctionDef("acos", "Arccosine (returns radians)", _math(np.arccos)),
    FunctionDef("atan", "Arctangent (returns radians)", _math(np.arctan)),
    FunctionDef(
        "atan2",
        "Two-argument arctangent (returns radians)",
        _math(np.arctan2),
        placeholder="${1:y}, ${2:x}",
    ),
    FunctionDef("deg2rad", "Convert degrees to radians", _deg2rad, placeholder="${1:deg}"),
    FunctionDef("rad2deg", "Convert radians to degrees", _rad2deg, placeholder="${1:rad}"),
    FunctionDef("wrap360", "Wrap angle to [0, 360) degrees", _wrap360, placeholder="${1:deg}"),
    FunctionDef("sqrt", "Square root", _math(np.sqrt)),
    FunctionDef("exp", "Exponential", _math(np.exp)),
    FunctionDef("log10", "Base-10 logarithm", _math(np.log10)),
    FunctionDef("ln", "Natural logarithm", _math(np.log)),
    FunctionDef("pow", "Raise x to the power y", _math(np.power), placeholder="${1:x}, ${2:y}"),
    FunctionDef("max", "Larger of two values", _extremum(np.maximum), placeholder="${1:x}, ${2:y}"),
    FunctionDef("min", "Smaller of two values", _extremum(np.minimum), placeholder="${1:x}, ${2:y}"),
    FunctionDef(
        "str",
        "Convert to text; slow, converts each value separately. Prefer text literals or text columns directly",
        _formula_str,
    ),
    FunctionDef(
        "where",
        "Pick then if cond is true, otherwise the third argument; nest for extra branches",
        _where,
        placeholder="${1:cond}, ${2:then}, ${3:else}",
    ),
    FunctionDef("abs", "Absolute value", _math(np.abs)),
    FunctionDef("floor", "Round down to an integer, keeping units", _math(np.floor)),
    FunctionDef("ceil", "Round up to an integer, keeping units", _math(np.ceil)),
    FunctionDef(
        "round",
        "Round to ndigits decimal places, keeping units",
        _round,
        placeholder="${1:x}, ${2:ndigits}",
    ),
    FunctionDef(
        "and_",
        "Logical AND of two or more conditions",
        _logical(np.logical_and),
        placeholder="${1:a}, ${2:b}",
    ),
    FunctionDef(
        "or_",
        "Logical OR of two or more conditions",
        _logical(np.logical_or),
        placeholder="${1:a}, ${2:b}",
    ),
    FunctionDef("not_", "Logical NOT of a condition", _not, placeholder="${1:cond}"),
    FunctionDef(
        "select",
        "Multi-way switch: value of the first true condition, otherwise the default; "
        "quantities are converted to the unit of the first quantity value",
        _select,
        placeholder="${1:cond1}, ${2:value1}, ${3:cond2}, ${4:value2}, ${5:default}",
    ),
    FunctionDef(
        "isin",
        "True where x equals any of the listed values (text or numbers)",
        _isin,
        placeholder="${1:x}, ${2:v1}, ${3:v2}",
    ),
    FunctionDef(
        "contains",
        "True where the text contains the substring",
        _string(_contains),
        placeholder="${1:s}, ${2:sub}",
    ),
    FunctionDef(
        "startswith",
        "True where the text starts with the prefix",
        _string(np.strings.startswith),
        placeholder="${1:s}, ${2:prefix}",
    ),
    FunctionDef(
        "endswith",
        "True where the text ends with the suffix",
        _string(np.strings.endswith),
        placeholder="${1:s}, ${2:suffix}",
    ),
    FunctionDef("upper", "Upper-case text", _string(np.strings.upper), placeholder="${1:s}"),
    FunctionDef("lower", "Lower-case text", _string(np.strings.lower), placeholder="${1:s}"),
    FunctionDef("strip", "Remove leading and trailing whitespace", _string(np.strings.strip), placeholder="${1:s}"),
    FunctionDef(
        "replace",
        "Replace all occurrences of old with new in text",
        _string(np.strings.replace),
        placeholder="${1:s}, ${2:old}, ${3:new}",
    ),
    FunctionDef(
        "slice",
        "Substring from start (inclusive) to stop (exclusive); negative indices count from the end",
        _string(np.strings.slice, numeric_args=(0, 1)),
        placeholder="${1:s}, ${2:start}, ${3:stop}",
    ),
    FunctionDef("len", "Text length", _string_count(np.strings.str_len), placeholder="${1:s}"),
    FunctionDef(
        "find",
        "Index of the first occurrence of sub in text, -1 if absent",
        _string_count(np.strings.find),
        placeholder="${1:s}, ${2:sub}",
    ),
    FunctionDef(
        "zfill",
        "Left-pad text with zeros to the given width",
        _string(np.strings.zfill, numeric_args=(0,)),
        placeholder="${1:s}, ${2:width}",
    ),
    FunctionDef(
        "num",
        "Parse text to a dimensionless number; fails on unparseable values",
        _num,
        placeholder="${1:s}",
    ),
    FunctionDef(
        "to_deg",
        'Convert to degrees; e.g. "00 02 08.4" (hourangle), "+16 35 13" (deg), "00h02m08.4s". '
        "Slow on text, parses each value separately. Prefer numeric columns with units, "
        'e.g. col("ra") or col("ra_h") / unit("h") * 15 * deg',
        _to_deg,
    ),
    FunctionDef(
        "unit",
        'Astropy unit from a name string; e.g. "Mpc", "km/s", "Jy"',
        _unit,
        placeholder='"${1:name}"',
    ),
)
