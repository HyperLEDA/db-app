import abc

import requests

from app.lib.web import errors
from app.specs import fieldapi as fieldapi_spec


class FieldAPIClient(abc.ABC):
    @abc.abstractmethod
    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        pass


class RequestsFieldAPIClient(FieldAPIClient):
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def sample_sfd_ebv(self, coordinates: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
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
