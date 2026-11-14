from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from astropy import units as u

from app.lib.formula import core, errors, values


@dataclass(frozen=True)
class OutputField:
    name: str
    data_type: str
    unit: str | None = None


_FLOAT_TYPES = frozenset({"float", "double", "double precision", "real", "number"})
_INT_TYPES = frozenset(
    {
        "short",
        "int",
        "long",
        "integer",
        "smallint",
        "unsignedLong",
        "unsignedInt",
        "unsignedShort",
        "unsignedByte",
        "positiveInteger",
    }
)


def prepare_batch(
    rows: Sequence[Mapping[str, Any]],
    referenced: Sequence[str],
    column_units: Mapping[str, str],
    id_column: str,
) -> tuple[list[Mapping[str, Any]], list[str], dict[str, values.Value]]:
    keep = np.ones(len(rows), dtype=bool)
    for column in referenced:
        keep &= np.fromiter((row.get(column) is not None for row in rows), dtype=bool, count=len(rows))
    kept = [row for row, flag in zip(rows, keep, strict=True) if flag]
    ids = [str(row[id_column]) for row in kept]
    columns = {
        column: values.column_quantity([row[column] for row in kept], column_units.get(column, ""))
        for column in referenced
    }
    return kept, ids, columns


def evaluate_batch(
    rows: Sequence[Mapping[str, Any]],
    output_columns: Sequence[str],
    expressions: Mapping[str, str],
    parsed: Mapping[str, core.Expression],
    fields_by_name: Mapping[str, OutputField],
    column_units: Mapping[str, str],
    id_column: str,
) -> tuple[list[str], list[list[Any]]]:
    referenced = sorted(set().union(*(expr.referenced_columns for expr in parsed.values())))
    kept, ids, columns = prepare_batch(rows, referenced, column_units, id_column)
    if not kept:
        return [], []

    results = [
        evaluate_field(fields_by_name[name], expressions[name], parsed[name], columns, column_units, kept, ids)
        for name in output_columns
    ]
    return ids, [list(row) for row in zip(*results, strict=True)]


def evaluate_field(
    field: OutputField,
    source: str,
    expression: core.Expression,
    columns: Mapping[str, values.Value],
    column_units: Mapping[str, str],
    rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
) -> list[Any]:
    if field.data_type in _FLOAT_TYPES or field.data_type in _INT_TYPES:
        return _evaluate_numeric(field, source, expression, columns, column_units, rows, ids)
    return _evaluate_text(field, source, expression, columns, column_units, len(rows))


def _evaluate_numeric(
    field: OutputField,
    source: str,
    expression: core.Expression,
    columns: Mapping[str, values.Value],
    column_units: Mapping[str, str],
    rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
) -> list[Any]:
    size = len(rows)
    try:
        with np.errstate(all="ignore"):
            quantity = _as_quantity(core.evaluate(expression, columns))
    except (errors.ExpressionEvaluationError, ValueError, u.UnitConversionError) as e:
        raise RuntimeError(
            f"failed to evaluate {field.name!r} ({source!r}){_context(expression, column_units)}: {e}"
        ) from e
    target = u.Unit(field.unit) if field.unit else u.Unit("")
    try:
        converted = np.asarray(quantity.to_value(target), dtype=float)
        if converted.shape == ():
            converted = np.full(size, converted.item())
        elif converted.shape != (size,):
            raise ValueError("expression must evaluate to a scalar value per row")
    except (ValueError, u.UnitConversionError) as e:
        raise RuntimeError(
            f"failed to convert {field.name!r} ({source!r}) to {field.unit or 'dimensionless'}"
            f"{_context(expression, column_units)}: {e}"
        ) from e
    _check_finite(field, source, expression, converted, rows, ids)
    if field.data_type in _INT_TYPES:
        return converted.astype(np.int64).tolist()
    return converted.tolist()


def _check_finite(
    field: OutputField,
    source: str,
    expression: core.Expression,
    numbers: np.ndarray,
    rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
) -> None:
    bad = np.flatnonzero(~np.isfinite(numbers))
    if len(bad) == 0:
        return
    first = int(bad[0])
    inputs = ", ".join(f"{column}={rows[first][column]!r}" for column in sorted(expression.referenced_columns))
    raise RuntimeError(
        f"{field.name!r} ({source!r}) produced {len(bad)} non-finite value(s) out of {len(numbers)} rows; "
        f"first at record {ids[first]}, value {numbers[first]!r}" + (f", inputs: {inputs}" if inputs else "")
    )


def _evaluate_text(
    field: OutputField,
    source: str,
    expression: core.Expression,
    columns: Mapping[str, values.Value],
    column_units: Mapping[str, str],
    size: int,
) -> list[str]:
    try:
        with np.errstate(all="ignore"):
            return values.value_to_str_list(core.evaluate(expression, columns), size)
    except (errors.ExpressionEvaluationError, ValueError, TypeError) as e:
        raise RuntimeError(
            f"failed to evaluate {field.name!r} ({source!r}){_context(expression, column_units)}: {e}"
        ) from e


def _context(expression: core.Expression, column_units: Mapping[str, str]) -> str:
    if not expression.referenced_columns:
        return ""
    parts = [f"{column}={column_units.get(column, '')!r}" for column in sorted(expression.referenced_columns)]
    return f"; columns: {', '.join(parts)}"


def _as_quantity(value: object) -> u.Quantity:
    if isinstance(value, u.Quantity):
        return value
    if isinstance(value, (np.ndarray, np.number, int, float)) and np.asarray(value).dtype.kind in "fiu":
        return np.asarray(value, dtype=float) * u.Unit("")
    raise ValueError(f"numeric expression must evaluate to a quantity, got {type(value).__name__}")
