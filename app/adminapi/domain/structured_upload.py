from typing import final

from app.adminapi.clients.prefect import PrefectClient
from app.catalogs import layer1
from app.lib.web.errors import NotFoundError
from app.specs import adminapi as spec


@final
class StructuredUploadManager:
    def __init__(self, prefect: PrefectClient) -> None:
        self._prefect = prefect

    def start(self, request: spec.StartStructuredUploadRequest) -> spec.StartStructuredUploadResponse:
        try:
            catalog = layer1.Catalog(request.catalog)
        except ValueError as exc:
            raise NotFoundError(entity_name="catalog", entity=request.catalog) from exc

        object_cls = layer1.get_catalog_object_type(catalog)
        flow_run_id = self._prefect.create_flow_run(
            name=f"{object_cls.title()}/upload-{catalog.value}",
            parameters={"params": request.params},
        )
        return spec.StartStructuredUploadResponse(flow_run_id=flow_run_id)
