from typing import final

from app.adminapi import cache, clients
from app.adminapi import presentation as adminapi
from app.adminapi.domain import catalogs, crossmatch, layer1_write, login, pgc, sources, table_upload
from app.data import repositories
from app.lib import auth
from app.lib.tap import types as tap_types

_ADMIN_TAP_SYNC_QUERY_TIMEOUT_SECONDS = 60


def _json_cell(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


@final
class Actions(adminapi.Actions):
    def __init__(
        self,
        common_repo: repositories.CommonRepository,
        layer0_repo: repositories.Layer0Repository,
        layer1_repo: repositories.Layer1Repository,
        layer2_repo: repositories.Layer2Repository,
        metadata_repo: repositories.MetadataRepository,
        authenticator: auth.Authenticator,
        clients: clients.Clients,
        table_stats_cache: cache.BackgroundCache[adminapi.TableStatsSnapshot],
    ):
        self.metadata_repo = metadata_repo
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
        self.pgc_manager = pgc.PgcManager(common_repo, layer0_repo)
        self.layer1_writer = layer1_write.Layer1Writer(layer1_repo)
        self.catalog_manager = catalogs.CatalogManager(layer1_repo)

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

    def get_catalogs(self) -> adminapi.GetCatalogsResponse:
        return self.catalog_manager.get_catalogs()

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

    def merge_pgcs(self, r: adminapi.MergePgcsRequest) -> adminapi.MergePgcsResponse:
        return self.pgc_manager.merge_pgcs(r)

    def tap_sync(self, request: adminapi.TAPSyncRequest) -> adminapi.TAPSyncResponse:
        result = self.metadata_repo.query_with_metadata(
            request.query,
            request.maxrec,
            timeout_seconds=_ADMIN_TAP_SYNC_QUERY_TIMEOUT_SECONDS,
        )
        columns: list[adminapi.TAPVOTableColumn] = []
        for col in result.columns:
            datatype = tap_types.python_to_tap_datatype(col.sample_value)
            columns.append(
                adminapi.TAPVOTableColumn(
                    name=col.column_name,
                    datatype=datatype,
                    arraysize="*" if datatype == "char" else None,
                )
            )
        data = [[_json_cell(cell) for cell in row] for row in result.rows]
        return adminapi.TAPSyncResponse(
            resource=adminapi.TAPVOTableResource(
                table=adminapi.TAPVOTableTable(columns=columns, data=data),
            )
        )
