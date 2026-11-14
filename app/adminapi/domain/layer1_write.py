from collections.abc import Mapping, Sequence
from typing import Any, final

import numpy as np
import psycopg
from astropy import units as u

from app.adminapi import repository
from app.adminapi.clients.prefect import PrefectClient
from app.catalogs import layer0, layer1
from app.lib import formula
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec


def _json_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    return str(value)


def _evaluate_field(
    field: formula.OutputField,
    source: str,
    expression: formula.Expression,
    columns: Mapping[str, formula.Value],
    column_units: Mapping[str, str],
    rows: Sequence[Mapping[str, Any]],
    ids: Sequence[str],
) -> tuple[list[Any], spec.PreviewFieldError | None]:
    try:
        return formula.evaluate_field(field, source, expression, columns, column_units, rows, ids), None
    except RuntimeError as batch_error:
        error = spec.PreviewFieldError(field=field.name, message=str(batch_error))

    for row, record_id in zip(rows, ids, strict=True):
        row_columns = {
            column: formula.column_quantity([row[column]], column_units.get(column, ""))
            for column in expression.referenced_columns
        }
        try:
            formula.evaluate_field(field, source, expression, row_columns, column_units, [row], [record_id])
        except RuntimeError as row_error:
            return [], spec.PreviewFieldError(field=field.name, message=str(row_error), record_id=record_id)
    return [], error


@final
class Layer1Writer:
    def __init__(self, repo: repository.Repository, prefect: PrefectClient) -> None:
        self._repo = repo
        self._prefect = prefect

    def save_data(self, request: spec.SaveStructuredDataRequest) -> spec.SaveStructuredDataResponse:
        catalog = layer1.Catalog(request.catalog)
        object_cls = layer1.get_catalog_object_type(catalog)
        table = object_cls.layer1_table()

        internal_units = self._repo.get_column_units(catalog)
        missing = [col for col in request.columns if col in internal_units and col not in request.units]
        if missing:
            raise RuleValidationError(f"units required for columns: {', '.join(sorted(missing))}")

        factors: list[float | None] = [None] * len(request.columns)
        for j, col in enumerate(request.columns):
            if col in internal_units and col in request.units:
                factors[j] = (1.0 * u.Unit(request.units[col])).to(u.Unit(internal_units[col])).value
            else:
                factors[j] = None

        converted = []
        for row in request.data:
            new_row = []
            for value, factor in zip(row, factors, strict=True):
                if factor is not None:
                    new_row.append(float(value) * factor)
                else:
                    new_row.append(value)
            converted.append(new_row)

        converted = layer1.normalize_catalog_rows(catalog, request.columns, converted)

        try:
            conflict_keys = object_cls.layer1_primary_keys()
            self._repo.save_structured_data(table, request.columns, request.ids, converted, conflict_keys=conflict_keys)
        except psycopg.errors.ForeignKeyViolation as e:
            raise RuleValidationError(layer1.format_foreign_key_violation(e)) from e

        return spec.SaveStructuredDataResponse()

    def start_upload(self, request: spec.StartStructuredUploadRequest) -> spec.StartStructuredUploadResponse:
        try:
            catalog = layer1.Catalog(request.catalog)
        except ValueError as exc:
            raise NotFoundError(entity_name="catalog", entity=request.catalog) from exc

        object_cls = layer1.get_catalog_object_type(catalog)
        task_id = self._prefect.create_flow_run(
            name=f"{object_cls.title()}/upload-{catalog.value}",
            parameters={"params": request.params},
        )
        return spec.StartStructuredUploadResponse(task_id=task_id)

    def preview_upload(self, request: spec.PreviewStructuredUploadRequest) -> spec.PreviewStructuredUploadResponse:
        try:
            catalog = layer1.Catalog(request.catalog)
        except ValueError as exc:
            raise NotFoundError(entity_name="catalog", entity=request.catalog) from exc

        object_cls = layer1.get_catalog_object_type(catalog)
        schema_name, layer1_table = object_cls.layer1_table().split(".", maxsplit=1)
        layer1_info = self._repo.get_table_metadata(schema_name, layer1_table)
        fields_by_name = {}
        for col in layer1.writable_columns(layer1_info):
            field = spec.field_from_column(col)
            fields_by_name[field.name] = formula.OutputField(field.name, field.data_type.value, field.unit)

        expressions = {name: source.strip() for name, source in request.expressions.items() if source.strip()}
        unknown = sorted(set(expressions) - set(fields_by_name))
        if unknown:
            raise RuleValidationError(f"unknown fields for catalog {catalog.value}: {', '.join(unknown)}")

        raw_info = self._repo.get_table_metadata(layer0.RAWDATA_SCHEMA, request.table_name)
        if not raw_info.columns:
            raise NotFoundError(entity_name="table", entity=request.table_name)
        column_units = {name: col.unit for name, col in raw_info.columns.items() if col.unit}

        errors: list[spec.PreviewFieldError] = []
        parsed: dict[str, formula.Expression] = {}
        for name, source in expressions.items():
            try:
                expression = formula.parse(source)
            except formula.ExpressionError as e:
                errors.append(spec.PreviewFieldError(field=name, message=str(e)))
                continue
            missing = sorted(expression.referenced_columns - set(raw_info.columns))
            if missing:
                errors.append(
                    spec.PreviewFieldError(
                        field=name, message=f"columns not found in {request.table_name}: {', '.join(missing)}"
                    )
                )
                continue
            parsed[name] = expression

        referenced = sorted(set().union(*(expr.referenced_columns for expr in parsed.values())))
        fetch_columns = [name for name in referenced if name != layer0.INTERNAL_ID_COLUMN_NAME]
        rows = self._repo.sample_rawdata(request.table_name, fetch_columns, request.limit)

        kept, ids, columns = formula.prepare_batch(rows, referenced, column_units, layer0.INTERNAL_ID_COLUMN_NAME)
        outputs: dict[str, list[Any]] = {}
        if kept:
            for name, expression in parsed.items():
                result, error = _evaluate_field(
                    fields_by_name[name], expressions[name], expression, columns, column_units, kept, ids
                )
                if error is not None:
                    errors.append(error)
                else:
                    outputs[name] = result

        kept_index = {id(row): index for index, row in enumerate(kept)}
        preview_rows: list[spec.PreviewRow] = []
        for row in rows:
            index = kept_index.get(id(row))
            skipped_reason = None
            if index is None:
                nulls = [column for column in referenced if row.get(column) is None]
                skipped_reason = f"null in {', '.join(nulls)}"
            preview_rows.append(
                spec.PreviewRow(
                    record_id=str(row[layer0.INTERNAL_ID_COLUMN_NAME]),
                    inputs={column: _json_value(row.get(column)) for column in referenced},
                    outputs={}
                    if index is None
                    else {name: _json_value(values[index]) for name, values in outputs.items()},
                    skipped_reason=skipped_reason,
                )
            )
        return spec.PreviewStructuredUploadResponse(rows=preview_rows, errors=errors)
