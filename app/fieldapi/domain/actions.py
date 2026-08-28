from typing import final

from app.fieldapi import presentation
from app.fieldapi.providers import registry
from app.specs import fieldapi


@final
class Actions(presentation.Actions):
    def __init__(self, dataset_registry: registry.DatasetRegistry) -> None:
        self.dataset_registry = dataset_registry

    def list_datasets(self) -> fieldapi.ListDatasetsResponse:
        return fieldapi.ListDatasetsResponse(datasets=self.dataset_registry.list_datasets())

    def sample(self, request: fieldapi.SampleRequest) -> fieldapi.SampleResponse:
        values = self.dataset_registry.sample(request.dataset, request.coordinates)
        return fieldapi.SampleResponse(values=values)
