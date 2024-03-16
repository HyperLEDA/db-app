import abc

from app.domain import model


class Actions(abc.ABC):
    def create_source(self, r: model.CreateSourceRequest) -> model.CreateSourceResponse:
        raise NotImplementedError("not implemented")

    def get_source(self, r: model.GetSourceRequest) -> model.GetSourceResponse:
        raise NotImplementedError("not implemented")

    def get_source_list(self, r: model.GetSourceListRequest) -> model.GetSourceListResponse:
        raise NotImplementedError("not implemented")

    def create_objects(self, r: model.CreateObjectBatchRequest) -> model.CreateObjectBatchResponse:
        raise NotImplementedError("not implemented")

    def create_object(self, r: model.CreateObjectRequest) -> model.CreateObjectResponse:
        raise NotImplementedError("not implemented")

    def get_object_names(self, r: model.GetObjectNamesRequest) -> model.GetObjectNamesResponse:
        raise NotImplementedError("not implemented")
