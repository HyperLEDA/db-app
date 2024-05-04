import abc

from app.domain import model


class Actions(abc.ABC):
    @abc.abstractmethod
    def create_source(self, r: model.CreateSourceRequest) -> model.CreateSourceResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_source(self, r: model.GetSourceRequest) -> model.GetSourceResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_source_list(self, r: model.GetSourceListRequest) -> model.GetSourceListResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_object_names(self, r: model.GetObjectNamesRequest) -> model.GetObjectNamesResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def search_catalogs(self, r: model.SearchCatalogsRequest) -> model.SearchCatalogsResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def start_task(self, r: model.StartTaskRequest) -> model.StartTaskResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def debug_start_task(self, r: model.StartTaskRequest) -> model.StartTaskResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_task_info(self, r: model.GetTaskInfoRequest) -> model.GetTaskInfoResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def create_table(self, r: model.CreateTableRequest) -> model.CreateTableResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def add_data(self, r: model.AddDataRequest) -> model.AddDataResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def login(self, r: model.LoginRequest) -> model.LoginResponse:
        raise NotImplementedError("not implemented")
