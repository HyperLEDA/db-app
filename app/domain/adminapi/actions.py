from typing import final

from app.data import repositories
from app.domain.adminapi import crossmatch, designation_rules, layer1_write, login, sources, table_upload
from app.lib import auth, cache, clients
from app.presentation import adminapi


@final
class Actions(adminapi.Actions):
    def __init__(
        self,
        common_repo: repositories.CommonRepository,
        layer0_repo: repositories.Layer0Repository,
        layer1_repo: repositories.Layer1Repository,
        layer2_repo: repositories.Layer2Repository,
        designation_rules_repo: repositories.DesignationRulesRepository,
        authenticator: auth.Authenticator,
        clients: clients.Clients,
        table_stats_cache: cache.BackgroundCache[adminapi.TableStatsSnapshot],
    ):
        self.source_manager = sources.SourceManager(common_repo)
        self.login_manager = login.LoginManager(authenticator)
        self.table_upload_manager = table_upload.TableUploadManager(
            common_repo,
            layer0_repo,
            layer1_repo,
            clients,
            table_stats_cache,
        )
        self.crossmatch_manager = crossmatch.CrossmatchManager(layer0_repo, layer1_repo, layer2_repo)
        self.layer1_writer = layer1_write.Layer1Writer(layer1_repo)
        self.designation_rules_manager = designation_rules.DesignationRulesManager(designation_rules_repo)

    def create_source(self, r: adminapi.CreateSourceRequest) -> adminapi.CreateSourceResponse:
        return self.source_manager.create_source(r)

    def login(self, r: adminapi.LoginRequest) -> adminapi.LoginResponse:
        return self.login_manager.login(r)

    def logout(self, token: str) -> adminapi.LogoutResponse:
        return self.login_manager.logout(token)

    def add_data(self, r: adminapi.AddDataRequest) -> adminapi.AddDataResponse:
        return self.table_upload_manager.add_data(r)

    def create_table(self, r: adminapi.CreateTableRequest) -> tuple[adminapi.CreateTableResponse, bool]:
        return self.table_upload_manager.create_table(r)

    def patch_table(self, r: adminapi.PatchTableRequest) -> adminapi.PatchTableResponse:
        return self.table_upload_manager.patch_table(r)

    def get_table(self, r: adminapi.GetTableRequest) -> adminapi.GetTableResponse:
        return self.table_upload_manager.get_table(r)

    def get_table_list(self, r: adminapi.GetTableListRequest) -> adminapi.GetTableListResponse:
        return self.table_upload_manager.get_table_list(r)

    def get_records(self, r: adminapi.GetRecordsRequest) -> adminapi.GetRecordsResponse:
        return self.table_upload_manager.get_records(r)

    def get_record_crossmatch(self, r: adminapi.GetRecordCrossmatchRequest) -> adminapi.GetRecordCrossmatchResponse:
        return self.crossmatch_manager.get_record_crossmatch(r)

    def save_structured_data(self, r: adminapi.SaveStructuredDataRequest) -> adminapi.SaveStructuredDataResponse:
        return self.layer1_writer.save_data(r)

    def set_crossmatch_results(self, r: adminapi.SetCrossmatchResultsRequest) -> adminapi.SetCrossmatchResultsResponse:
        return self.crossmatch_manager.set_crossmatch_results(r)

    def assign_record_pgcs(self, r: adminapi.AssignRecordPgcsRequest) -> adminapi.AssignRecordPgcsResponse:
        return self.crossmatch_manager.assign_record_pgcs(r)

    def list_designation_rules(self) -> adminapi.ListRulesResponse:
        return self.designation_rules_manager.list_rules()

    def save_designation_rule(self, r: adminapi.SaveRuleRequest) -> adminapi.SaveRuleResponse:
        return self.designation_rules_manager.save_rule(r)
