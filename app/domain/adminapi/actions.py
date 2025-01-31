from typing import final

from app.data import repositories
from app.domain.adminapi import login, sources, table_transfer, table_upload, tasks
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
        self.table_transfer_manager = table_transfer.TableTransferManager(
            common_repo, layer0_repo, layer1_repo, layer2_repo
        )

    def create_source(self, r: adminapi.CreateSourceRequest) -> adminapi.CreateSourceResponse:
        return self.source_manager.create_source(r)

    def get_source(self, r: adminapi.GetSourceRequest) -> adminapi.GetSourceResponse:
        return self.source_manager.get_source(r)

    def start_task(self, r: adminapi.StartTaskRequest) -> adminapi.StartTaskResponse:
        return self.task_manager.start_task(r)

    def get_task_info(self, r: adminapi.GetTaskInfoRequest) -> adminapi.GetTaskInfoResponse:
        return self.task_manager.get_task_info(r)

    def login(self, r: adminapi.LoginRequest) -> adminapi.LoginResponse:
        return self.login_manager.login(r)

    def add_data(self, r: adminapi.AddDataRequest) -> adminapi.AddDataResponse:
        return self.table_upload_manager.add_data(r)

    def create_table(self, r: adminapi.CreateTableRequest) -> tuple[adminapi.CreateTableResponse, bool]:
        return self.table_upload_manager.create_table(r)

    def set_table_status(self, r: adminapi.SetTableStatusRequest) -> adminapi.SetTableStatusResponse:
        return self.table_transfer_manager.set_table_status(r)

    def table_process(self, r: adminapi.TableProcessRequest) -> adminapi.TableProcessResponse:
        return self.table_transfer_manager.table_process(r)

    def table_status_stats(self, r: adminapi.TableStatusStatsRequest) -> adminapi.TableStatusStatsResponse:
        return self.table_transfer_manager.table_status_stats(r)
