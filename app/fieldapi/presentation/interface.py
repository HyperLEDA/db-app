import abc

from app.specs import fieldapi as spec


class Actions(abc.ABC):
    @abc.abstractmethod
    def list_datasets(self) -> spec.ListDatasetsResponse:
        pass

    @abc.abstractmethod
    def sample(self, request: spec.SampleRequest) -> spec.SampleResponse:
        pass
