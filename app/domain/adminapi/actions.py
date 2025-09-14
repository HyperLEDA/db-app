from typing import final

from app.data import repositories
from app.domain.adminapi import crossmatch, login, sources, table_upload, tasks
from app.lib import auth, clients
from app.presentation import adminapi


@final
class Actions(adminapi.Actions):
    def __init__(
        self,
        common_repo: repositories.CommonRepository,
        layer0_repo: repositories.Layer0Repository,
        layer1_repo: repositories.Layer1Repository,
        layer2_repo: repositories.Layer2Repository,
        queue_repo: repositories.QueueRepository,
        authenticator: auth.Authenticator,
        clients: clients.Clients,
    ):
        self.source_manager = sources.SourceManager(common_repo)
        self.task_manager = tasks.TaskManager(common_repo, queue_repo)
        self.login_manager = login.LoginManager(authenticator)
        self.table_upload_manager = table_upload.TableUploadManager(common_repo, layer0_repo, clients)
        self.crossmatch_manager = crossmatch.CrossmatchManager(layer0_repo)

    def create_source(self, r: adminapi.CreateSourceRequest) -> adminapi.CreateSourceResponse:
        return self.source_manager.create_source(r)

    def get_task_info(self, r: adminapi.GetTaskInfoRequest) -> adminapi.GetTaskInfoResponse:
        return self.task_manager.get_task_info(r)

    def login(self, r: adminapi.LoginRequest) -> adminapi.LoginResponse:
        return self.login_manager.login(r)

    def add_data(self, r: adminapi.AddDataRequest) -> adminapi.AddDataResponse:
        return self.table_upload_manager.add_data(r)

    def create_table(self, r: adminapi.CreateTableRequest) -> tuple[adminapi.CreateTableResponse, bool]:
        return self.table_upload_manager.create_table(r)

    def patch_table(self, r: adminapi.PatchTableRequest) -> adminapi.PatchTableResponse:
        return self.table_upload_manager.patch_table(r)

    def create_marking(self, r: adminapi.CreateMarkingRequest) -> adminapi.CreateMarkingResponse:
        return self.table_upload_manager.create_marking(r)

    def get_table(self, r: adminapi.GetTableRequest) -> adminapi.GetTableResponse:
        return self.table_upload_manager.get_table(r)

    def get_crossmatch_records(self, r: adminapi.GetRecordsCrossmatchRequest) -> adminapi.GetRecordsCrossmatchResponse:
        return self.crossmatch_manager.get_crossmatch_records(r)
