import abc

from app.specs.adminapi import interface, records, tap


class Actions(abc.ABC):
    @abc.abstractmethod
    def add_data(self, r: interface.AddDataRequest) -> interface.AddDataResponse:
        pass

    @abc.abstractmethod
    def create_table(self, r: interface.CreateTableRequest) -> tuple[interface.CreateTableResponse, bool]:
        pass

    @abc.abstractmethod
    def get_table(self, r: interface.GetTableRequest) -> interface.GetTableResponse:
        pass

    @abc.abstractmethod
    def get_table_list(self, r: interface.GetTableListRequest) -> interface.GetTableListResponse:
        pass

    @abc.abstractmethod
    def get_catalogs(self) -> interface.GetCatalogsResponse:
        pass

    @abc.abstractmethod
    def patch_table(self, r: interface.PatchTableRequest) -> interface.PatchTableResponse:
        pass

    @abc.abstractmethod
    def create_source(self, r: interface.CreateSourceRequest) -> interface.CreateSourceResponse:
        pass

    @abc.abstractmethod
    def login(self, r: interface.LoginRequest) -> interface.LoginResponse:
        pass

    @abc.abstractmethod
    def logout(self, token: str) -> interface.LogoutResponse:
        pass

    @abc.abstractmethod
    def register(self, r: interface.RegisterRequest) -> interface.RegisterResponse:
        pass

    @abc.abstractmethod
    def get_records(self, r: records.GetRecordsRequest) -> records.GetRecordsResponse:
        pass

    @abc.abstractmethod
    def get_record_crossmatch(self, r: interface.GetRecordCrossmatchRequest) -> interface.GetRecordCrossmatchResponse:
        pass

    @abc.abstractmethod
    def save_structured_data(self, r: interface.SaveStructuredDataRequest) -> interface.SaveStructuredDataResponse:
        pass

    @abc.abstractmethod
    def set_crossmatch_results(
        self, r: interface.SetCrossmatchResultsRequest
    ) -> interface.SetCrossmatchResultsResponse:
        pass

    @abc.abstractmethod
    def assign_record_pgcs(self, r: interface.AssignRecordPgcsRequest) -> interface.AssignRecordPgcsResponse:
        pass

    @abc.abstractmethod
    def merge_pgcs(self, r: interface.MergePgcsRequest) -> interface.MergePgcsResponse:
        pass

    @abc.abstractmethod
    def tap_sync(self, request: tap.TAPSyncRequest) -> tap.TAPSyncResponse:
        pass
