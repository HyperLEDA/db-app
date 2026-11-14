from collections.abc import Callable, Mapping
from typing import Any, final
from uuid import UUID

from prefect.deployments import run_deployment

from app.adminapi import repository
from app.catalogs import layer1
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec


def _require_params(schema: spec.CatalogSchema, params: Mapping[str, Any]) -> dict[str, Any]:
    table_name = params.get("table_name")
    if not isinstance(table_name, str) or not table_name.strip():
        raise RuleValidationError("table_name is required")

    values = dict(params)
    for field in schema.fields:
        raw = values.get(field.name, "")
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            raise RuleValidationError(f"{field.name} must be a string expression")
        if field.required and not raw.strip():
            raise RuleValidationError(f"{field.name} is required")
        values[field.name] = raw

    write = values.get("write", True)
    if not isinstance(write, bool):
        raise RuleValidationError("write must be a boolean")
    values["write"] = write

    batch_size = values.get("batch_size", 10_000)
    if not isinstance(batch_size, int) or isinstance(batch_size, bool) or not 1 <= batch_size <= 500_000:
        raise RuleValidationError("batch_size must be an integer between 1 and 500000")
    values["batch_size"] = batch_size
    values["table_name"] = table_name.strip()
    return values


@final
class StructuredUploadManager:
    def __init__(
        self,
        repo: repository.Repository,
        *,
        start_deployment: Callable[..., Any] | None = None,
    ) -> None:
        self._repo = repo
        self._start_deployment = start_deployment or run_deployment

    def start(self, request: spec.StartStructuredUploadRequest) -> spec.StartStructuredUploadResponse:
        try:
            catalog = layer1.Catalog(request.catalog)
        except ValueError as exc:
            raise NotFoundError(entity_name="catalog", entity=request.catalog) from exc

        object_cls = layer1.get_catalog_object_type(catalog)
        schema_name, table_name = object_cls.layer1_table().split(".", maxsplit=1)
        table_info = self._repo.get_table_metadata(schema_name, table_name)
        schema = spec.CatalogSchema(
            catalog=catalog.value,
            title=object_cls.title(),
            description=object_cls.description(),
            fields=[spec.field_from_column(col) for col in layer1.writable_columns(table_info)],
        )
        params = _require_params(schema, request.params)

        flow_run = self._start_deployment(
            name=f"{object_cls.title()}/upload-{catalog.value}",
            parameters={"params": params},
            timeout=0,
        )
        flow_run_id = flow_run.id if isinstance(flow_run.id, UUID) else UUID(str(flow_run.id))
        return spec.StartStructuredUploadResponse(flow_run_id=str(flow_run_id))
