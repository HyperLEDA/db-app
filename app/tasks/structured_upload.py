import time
from collections.abc import Mapping, Sequence
from typing import Any

import pydantic
import structlog

from app.catalogs import layer0, layer1
from app.lib import formula
from app.specs import adminapi as spec
from app.tasks import artifacts, layer2_common, repository

_RESERVED_PARAMETERS = frozenset({"table_name", "write", "batch_size"})
_PREVIEW_ROWS = 5


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
    field_defs["write"] = (bool, pydantic.Field(default=True, description="Write rows into the catalog"))
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
    ) -> None:
        super().__init__(logger)
        self._catalog = catalog
        self._params = dict(params)

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
        fields_by_name = {
            field.name: formula.OutputField(field.name, field.data_type.value, field.unit) for field in schema.fields
        }
        progress = artifacts.ProgressTracker()
        progress.update(0, "Reading raw data")
        total = self.repository.get_table_record_count(table_name)
        if total == 0:
            progress.update(100, "Finished")
            return
        processed = 0
        preview_sent = False
        write = bool(values["write"])
        fetch_columns = [name for name in sorted(needed) if name != layer0.INTERNAL_ID_COLUMN_NAME]
        total_pages, rows_per_page = self.repository.get_rawdata_page_stats(table_name)
        pages_per_batch = max(1, round(int(values["batch_size"]) / rows_per_page))
        run_started = time.perf_counter()
        for start_page in range(0, total_pages, pages_per_batch):
            pages = min(pages_per_batch, total_pages - start_page)
            batch_started = time.perf_counter()
            rows = self.repository.fetch_rawdata_pages(
                table_name, fetch_columns, start_page, start_page + pages_per_batch
            )
            processed += len(rows)
            ids, data = formula.evaluate_batch(
                rows,
                output_columns,
                expressions,
                parsed,
                fields_by_name,
                column_units,
                layer0.INTERNAL_ID_COLUMN_NAME,
            )
            rows_read = len(rows)
            rows_kept = len(ids)
            rows_dropped = rows_read - rows_kept
            rows_written = 0
            if write and ids:
                self.repository.save_structured_data(self._catalog, output_columns, ids, data)
                rows_written = rows_kept
            elif ids and not write and not preview_sent:
                artifacts.emit_preview_table(_preview_rows(output_columns, ids, data), "Dry-run preview")
                preview_sent = True
            pages_done = min(start_page + pages_per_batch, total_pages)
            elapsed_s = time.perf_counter() - run_started
            eta_s = round(elapsed_s * (total_pages - pages_done) / pages_done) if pages_done < total_pages else 0
            self.log.info(
                "Processed batch",
                start_page=start_page,
                pages=pages,
                rows_read=rows_read,
                rows_kept=rows_kept,
                rows_dropped=rows_dropped,
                rows_written=rows_written,
                processed=processed,
                total=total,
                duration_ms=round((time.perf_counter() - batch_started) * 1000, 1),
                eta_s=eta_s,
            )
            progress.update(min(99, int(100 * pages_done / total_pages)), f"Processed {processed} / {total} rows")
        progress.update(100, "Finished")


def _preview_rows(columns: Sequence[str], ids: Sequence[str], data: Sequence[Sequence[Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(min(_PREVIEW_ROWS, len(ids))):
        row: dict[str, Any] = {"id": ids[index]}
        for name, value in zip(columns, data[index], strict=True):
            row[name] = value
        rows.append(row)
    return rows


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
