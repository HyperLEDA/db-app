import abc

from app.specs import adminapi as spec


class Actions(abc.ABC):
    @abc.abstractmethod
    def add_data(self, r: spec.AddDataRequest) -> spec.AddDataResponse:
        pass

    @abc.abstractmethod
    def create_table(self, r: spec.CreateTableRequest) -> tuple[spec.CreateTableResponse, bool]:
        pass

    @abc.abstractmethod
    def get_table(self, r: spec.GetTableRequest) -> spec.GetTableResponse:
        pass

    @abc.abstractmethod
    def get_table_list(self, r: spec.GetTableListRequest) -> spec.GetTableListResponse:
        pass

    @abc.abstractmethod
    def get_catalogs(self) -> spec.GetCatalogsResponse:
        pass

    @abc.abstractmethod
    def patch_table(self, r: spec.PatchTableRequest) -> spec.PatchTableResponse:
        pass

    @abc.abstractmethod
    def create_source(self, r: spec.CreateSourceRequest) -> spec.CreateSourceResponse:
        pass

    @abc.abstractmethod
    def login(self, r: spec.LoginRequest) -> spec.LoginResponse:
        pass

    @abc.abstractmethod
    def logout(self, token: str) -> spec.LogoutResponse:
        pass

    @abc.abstractmethod
    def register(self, r: spec.RegisterRequest) -> spec.RegisterResponse:
        pass

    @abc.abstractmethod
    def get_records(self, r: spec.GetRecordsRequest) -> spec.GetRecordsResponse:
        pass

    @abc.abstractmethod
    def get_record_crossmatch(self, r: spec.GetRecordCrossmatchRequest) -> spec.GetRecordCrossmatchResponse:
        pass

    @abc.abstractmethod
    def save_structured_data(self, r: spec.SaveStructuredDataRequest) -> spec.SaveStructuredDataResponse:
        pass

    @abc.abstractmethod
    def set_crossmatch_results(self, r: spec.SetCrossmatchResultsRequest) -> spec.SetCrossmatchResultsResponse:
        pass

    @abc.abstractmethod
    def assign_record_pgcs(self, r: spec.AssignRecordPgcsRequest) -> spec.AssignRecordPgcsResponse:
        pass

    @abc.abstractmethod
    def merge_pgcs(self, r: spec.MergePgcsRequest) -> spec.MergePgcsResponse:
        pass

    @abc.abstractmethod
    def tap_sync(self, request: spec.TAPSyncRequest) -> spec.TAPSyncResponse:
        pass
