from collections.abc import Mapping, Sequence
from typing import Any, final

from app.adminapi import repository
from app.catalogs import layer0, layer1
from app.lib import formula
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec


def _json_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
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
class StructuredPreview:
    def __init__(self, repo: repository.Repository) -> None:
        self._repo = repo

    def preview(self, request: spec.PreviewStructuredUploadRequest) -> spec.PreviewStructuredUploadResponse:
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
        rows = self._repo.sample_rawdata(request.table_name, fetch_columns, request.limit, request.sample == "random")

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
