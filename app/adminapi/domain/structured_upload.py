import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from types import SimpleNamespace
from typing import Any, final
from uuid import UUID

from app.catalogs import layer1
from app.lib.web.errors import InternalError, NotFoundError, RuleValidationError
from app.specs import adminapi as spec


def _prefect_request(method: str, url: str, body: Mapping[str, Any] | None = None) -> dict[str, Any]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()
        if exc.code == 404:
            raise NotFoundError(entity_name="deployment", entity=url) from exc
        if exc.code in {409, 422}:
            raise RuleValidationError(detail) from exc
        raise InternalError(f"prefect API error {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise InternalError(f"prefect API unreachable: {exc}") from exc


@final
class StructuredUploadManager:
    def __init__(
        self,
        *,
        prefect_api_url: str,
        start_deployment: Callable[..., Any] | None = None,
    ) -> None:
        self._prefect_api_url = prefect_api_url.rstrip("/")
        self._start_deployment = start_deployment or self._create_prefect_flow_run

    def _create_prefect_flow_run(
        self,
        *,
        name: str,
        parameters: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SimpleNamespace:
        del timeout
        if not self._prefect_api_url:
            raise InternalError("prefect.api_url is not configured")
        try:
            flow_name, deployment_name = name.split("/", 1)
        except ValueError as exc:
            raise RuleValidationError(f"invalid deployment name: {name}") from exc

        deployment_url = (
            f"{self._prefect_api_url}/deployments/name/"
            f"{urllib.parse.quote(flow_name, safe='')}/"
            f"{urllib.parse.quote(deployment_name, safe='')}"
        )
        deployment = _prefect_request("GET", deployment_url)
        flow_run = _prefect_request(
            "POST",
            f"{self._prefect_api_url}/deployments/{deployment['id']}/create_flow_run",
            {"parameters": parameters or {}},
        )
        return SimpleNamespace(id=flow_run["id"])

    def start(self, request: spec.StartStructuredUploadRequest) -> spec.StartStructuredUploadResponse:
        try:
            catalog = layer1.Catalog(request.catalog)
        except ValueError as exc:
            raise NotFoundError(entity_name="catalog", entity=request.catalog) from exc

        object_cls = layer1.get_catalog_object_type(catalog)
        flow_run = self._start_deployment(
            name=f"{object_cls.title()}/upload-{catalog.value}",
            parameters={"params": request.params},
            timeout=0,
        )
        flow_run_id = flow_run.id if isinstance(flow_run.id, UUID) else UUID(str(flow_run.id))
        return spec.StartStructuredUploadResponse(flow_run_id=str(flow_run_id))
