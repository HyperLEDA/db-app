import abc

from app.specs.fieldapi import interface


class Actions(abc.ABC):
    @abc.abstractmethod
    def list_datasets(self) -> interface.ListDatasetsResponse:
        pass

    @abc.abstractmethod
    def sample(self, request: interface.SampleRequest) -> interface.SampleResponse:
        pass
