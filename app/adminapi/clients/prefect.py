import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any, final

from app.lib.web.errors import InternalError, NotFoundError, RuleValidationError


def _request(method: str, url: str, body: Mapping[str, Any] | None = None) -> dict[str, Any]:
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
class PrefectClient:
    def __init__(self, api_url: str) -> None:
        self._api_url = api_url.rstrip("/")

    def create_flow_run(self, name: str, parameters: Mapping[str, Any] | None = None) -> str:
        if not self._api_url:
            raise InternalError("prefect.api_url is not configured")
        try:
            flow_name, deployment_name = name.split("/", 1)
        except ValueError as exc:
            raise RuleValidationError(f"invalid deployment name: {name}") from exc

        deployment = _request(
            "GET",
            (
                f"{self._api_url}/deployments/name/"
                f"{urllib.parse.quote(flow_name, safe='')}/"
                f"{urllib.parse.quote(deployment_name, safe='')}"
            ),
        )
        flow_run = _request(
            "POST",
            f"{self._api_url}/deployments/{deployment['id']}/create_flow_run",
            {"parameters": dict(parameters or {})},
        )
        return str(flow_run["id"])
