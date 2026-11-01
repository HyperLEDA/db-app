import abc

import requests

from app.lib.web import errors
from app.specs.fieldapi import interface as fieldapi_spec


class FieldAPIClient(abc.ABC):
    @abc.abstractmethod
    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        pass


class RequestsFieldAPIClient(FieldAPIClient):
    def __init__(self, base_url: str | None, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._timeout_seconds = timeout_seconds

    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        if self._base_url is None:
            raise errors.InternalError("field API base URL is not configured")
        request = fieldapi_spec.SampleRequest(dataset="sfd", coordinates=coordinates)
        try:
            response = requests.post(
                f"{self._base_url}/api/v1/sample",
                json=request.model_dump(),
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise errors.InternalError(exc) from exc

        payload = fieldapi_spec.SampleResponse.model_validate(response.json()["data"])
        return payload.values
