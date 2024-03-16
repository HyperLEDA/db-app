import abc

from app.domain import model


class Actions(abc.ABC):
    def create_source(self, r: model.CreateSourceRequest) -> model.CreateSourceResponse:
        raise NotImplementedError()

    def get_source(self, r: model.GetSourceRequest) -> model.GetSourceResponse:
        raise NotImplementedError()

    def get_source_list(self, r: model.GetSourceListRequest) -> model.GetSourceListResponse:
        raise NotImplementedError()

    def create_objects(self, r: model.CreateObjectBatchRequest) -> model.CreateObjectBatchResponse:
        raise NotImplementedError()
