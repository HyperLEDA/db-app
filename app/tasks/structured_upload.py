from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import pydantic
import structlog
from astropy import units as u

from app.catalogs import layer0, layer1
from app.lib import containers
from app.specs import adminapi as spec
from app.tasks import formula, layer2_common, repository

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
_RESERVED_PARAMETERS = frozenset({"table_name", "write", "batch_size"})
_PREVIEW_ROWS = 5

ProgressCallback = Callable[[float, str], None]
PreviewCallback = Callable[[list[dict[str, Any]], str], None]


def build_catalog_schema(repo: repository.Repository, catalog: layer1.Catalog) -> spec.CatalogSchema:
    object_cls = layer1.get_catalog_object_type(catalog)
    schema_name, table_name = object_cls.layer1_table().split(".", maxsplit=1)
    table_info = repo.get_table_metadata(schema_name, table_name)
    return spec.CatalogSchema(
        catalog=catalog.value,
        title=object_cls.title(),
        description=object_cls.description(),
        fields=[spec.field_from_column(col) for col in layer1.writable_columns(table_info)],
    )


def build_catalog_schemas(repo: repository.Repository) -> list[spec.CatalogSchema]:
    return [build_catalog_schema(repo, catalog) for catalog in layer1.Catalog]


def build_catalog_params_model(schema: spec.CatalogSchema) -> type[pydantic.BaseModel]:
    field_defs: dict[str, Any] = {
        "table_name": (str, pydantic.Field(min_length=1, description="Raw data table name")),
    }
    for field in schema.fields:
        if field.name in _RESERVED_PARAMETERS or not field.name.isidentifier():
            raise RuntimeError(f"catalog column {field.name!r} cannot be a task parameter")
        description = _field_description(field)
        if field.required:
            field_defs[field.name] = (formula.ExpressionStr, pydantic.Field(description=description))
        else:
            field_defs[field.name] = (formula.ExpressionStr, pydantic.Field(default="", description=description))
    field_defs["write"] = (bool, pydantic.Field(default=False, description="Write rows into the catalog"))
    field_defs["batch_size"] = (
        int,
        pydantic.Field(default=10_000, ge=1, le=500_000, description="Rows read per batch"),
    )
    model_name = "".join(part.capitalize() for part in schema.catalog.split("_")) + "UploadParams"
    return pydantic.create_model(model_name, **field_defs)


class StructuredCatalogUploadTask(layer2_common.Layer2StorageTask):
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        catalog: layer1.Catalog,
        params: Mapping[str, Any],
        on_progress: ProgressCallback | None = None,
        on_preview_table: PreviewCallback | None = None,
    ) -> None:
        super().__init__(logger)
        self._catalog = catalog
        self._params = dict(params)
        self._on_progress = on_progress
        self._on_preview_table = on_preview_table

    @classmethod
    def name(cls) -> str:
        return "structured-catalog-upload"

    def run(self) -> None:
        schema = build_catalog_schema(self.repository, self._catalog)
        form = build_catalog_params_model(schema).model_validate(self._params)
        values = form.model_dump()
        expressions = _selected_expressions(schema, values)
        parsed = {name: formula.parse(source) for name, source in expressions.items()}
        needed = set().union(*(expr.referenced_columns for expr in parsed.values()))
        table_name = str(values["table_name"])
        raw_info = self.repository.get_table_metadata(layer0.RAWDATA_SCHEMA, table_name)
        _require_columns(table_name, needed, set(raw_info.columns))
        column_units = {name: col.unit for name, col in raw_info.columns.items() if col.unit}
        output_columns = [field.name for field in schema.fields if field.name in expressions]
        fields_by_name = {field.name: field for field in schema.fields}
        self._report(0, "Reading raw data")
        total = self.repository.get_table_record_count(table_name)
        if total == 0:
            self._report(100, "Finished")
            return
        processed = 0
        preview_sent = False
        fetch_columns = [name for name in sorted(needed) if name != layer0.INTERNAL_ID_COLUMN_NAME]
        for _, rows in containers.read_batches(
            self.repository.fetch_rawdata_batch,
            lambda batch: len(batch) == 0,
            "",
            lambda batch, _: str(batch[-1][layer0.INTERNAL_ID_COLUMN_NAME]),
            table_name,
            fetch_columns,
            batch_size=int(values["batch_size"]),
        ):
            processed += len(rows)
            ids, data = _evaluate_batch(
                rows,
                output_columns,
                expressions,
                parsed,
                fields_by_name,
                column_units,
            )
            if values["write"] and ids:
                self.repository.save_structured_data(self._catalog, output_columns, ids, data)
            elif ids and not values["write"] and not preview_sent:
                self._emit_preview(output_columns, ids, data)
                preview_sent = True
            self._report(min(99, int(100 * processed / total)), f"Processed {processed} / {total} rows")
        self._report(100, "Finished")

    def _report(self, progress: float, description: str) -> None:
        if self._on_progress is not None:
            self._on_progress(progress, description)

    def _emit_preview(self, columns: Sequence[str], ids: Sequence[str], data: Sequence[Sequence[Any]]) -> None:
        if self._on_preview_table is None:
            return
        rows: list[dict[str, Any]] = []
        for index in range(min(_PREVIEW_ROWS, len(ids))):
            row: dict[str, Any] = {"id": ids[index]}
            for name, value in zip(columns, data[index], strict=True):
                row[name] = value
            rows.append(row)
        self._on_preview_table(rows, "Dry-run preview")


def _field_description(field: spec.CatalogField) -> str:
    text = field.description.strip() or field.name
    detail = field.data_type.value
    if field.unit:
        detail = f"{detail}, {field.unit}"
    if text == field.name:
        return f"{field.name} ({detail})"
    return f"{text} ({detail})"


def _selected_expressions(schema: spec.CatalogSchema, values: Mapping[str, Any]) -> dict[str, str]:
    selected: dict[str, str] = {}
    for field in schema.fields:
        source = str(values[field.name]).strip()
        if field.required and not source:
            raise RuntimeError(f"{field.name} is required")
        if source:
            selected[field.name] = source
    if not selected:
        raise RuntimeError("no catalog columns selected")
    return selected


def _require_columns(table_name: str, needed: set[str], available: set[str]) -> None:
    missing = sorted(needed - available)
    if missing:
        raise RuntimeError(f"columns not found in {table_name}: {', '.join(missing)}")


def _evaluate_batch(
    rows: Sequence[Mapping[str, Any]],
    output_columns: Sequence[str],
    expressions: Mapping[str, str],
    parsed: Mapping[str, formula.Expression],
    fields_by_name: Mapping[str, spec.CatalogField],
    column_units: Mapping[str, str],
) -> tuple[list[str], list[list[Any]]]:
    ids: list[str] = []
    data: list[list[Any]] = []
    referenced = _referenced_columns(parsed)
    for row in rows:
        if any(row.get(column) is None for column in referenced):
            continue
        values = {column: formula.column_quantity(row[column], column_units.get(column, "")) for column in referenced}
        ids.append(str(row[layer0.INTERNAL_ID_COLUMN_NAME]))
        data.append(
            [
                _evaluate_field(
                    fields_by_name[name],
                    expressions[name],
                    parsed[name],
                    values,
                    column_units,
                )
                for name in output_columns
            ]
        )
    return ids, data


def _referenced_columns(parsed: Mapping[str, formula.Expression]) -> set[str]:
    return set().union(*(expr.referenced_columns for expr in parsed.values()))


def _evaluate_field(
    field: spec.CatalogField,
    source: str,
    expression: formula.Expression,
    columns: Mapping[str, formula.Value],
    column_units: Mapping[str, str],
) -> Any:
    if field.data_type.value in _FLOAT_TYPES or field.data_type.value in _INT_TYPES:
        return _evaluate_numeric(field, source, expression, columns, column_units)
    return _evaluate_text(field, source, expression, columns, column_units)


def _evaluate_numeric(
    field: spec.CatalogField,
    source: str,
    expression: formula.Expression,
    columns: Mapping[str, formula.Value],
    column_units: Mapping[str, str],
) -> float | int:
    try:
        quantity = _as_quantity(formula.evaluate(expression, columns))
    except (formula.ExpressionEvaluationError, ValueError, u.UnitConversionError) as e:
        raise RuntimeError(
            f"failed to evaluate {field.name!r} ({source!r}){_context(expression, column_units)}: {e}"
        ) from e
    target = u.Unit(field.unit) if field.unit else u.Unit("")
    try:
        converted = quantity.to(target)
        value = _scalar_numeric(converted)
    except (ValueError, u.UnitConversionError) as e:
        raise RuntimeError(
            f"failed to convert {field.name!r} ({source!r}) to {field.unit or 'dimensionless'}"
            f"{_context(expression, column_units)}: {e}"
        ) from e
    if field.data_type.value in _INT_TYPES:
        return int(value)
    return value


def _evaluate_text(
    field: spec.CatalogField,
    source: str,
    expression: formula.Expression,
    columns: Mapping[str, formula.Value],
    column_units: Mapping[str, str],
) -> str:
    try:
        return formula.value_to_str(formula.evaluate(expression, columns))
    except (formula.ExpressionEvaluationError, ValueError, TypeError) as e:
        raise RuntimeError(
            f"failed to evaluate {field.name!r} ({source!r}){_context(expression, column_units)}: {e}"
        ) from e


def _context(expression: formula.Expression, column_units: Mapping[str, str]) -> str:
    if not expression.referenced_columns:
        return ""
    parts = [f"{column}={column_units.get(column, '')!r}" for column in sorted(expression.referenced_columns)]
    return f"; columns: {', '.join(parts)}"


def _as_quantity(value: object) -> u.Quantity:
    if isinstance(value, u.Quantity):
        return value
    if isinstance(value, np.ndarray) and value.shape == ():
        value = value.item()
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise ValueError(f"numeric expression must evaluate to a quantity, got {type(value).__name__}")
    return float(value) * u.Unit("")


def _scalar_numeric(quantity: u.Quantity) -> float:
    scalar = quantity.value
    if isinstance(scalar, np.ndarray):
        if scalar.shape != ():
            raise ValueError("expression must evaluate to a scalar value per row")
        scalar = scalar.item()
    if isinstance(scalar, bool):
        raise ValueError("numeric expression must evaluate to a quantity, got bool")
    return float(scalar)
