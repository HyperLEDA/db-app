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

    def search_catalogs(self, r: model.SearchCatalogsRequest) -> model.SearchCatalogsResponse:
        raise NotImplementedError("not implemented")

    def choose_table(self, r: model.ChooseTableRequest) -> model.ChooseTableResponse:
        raise NotImplementedError("not implemented")

    def start_task(self, r: model.StartTaskRequest) -> model.StartTaskResponse:
        raise NotImplementedError("not implemented")

    def get_task_info(self, r: model.GetTaskInfoRequest) -> model.GetTaskInfoResponse:
        raise NotImplementedError("not implemented")
