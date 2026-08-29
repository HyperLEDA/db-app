from typing import final

from app.adminapi import cache, clients, repository
from app.adminapi.domain import auth as admin_auth
from app.adminapi.domain import catalogs, crossmatch, layer1_write, pgc, sources, table_upload
from app.adminapi.presentation import interface
from app.lib import auth
from app.lib.storage import postgres
from app.lib.tap import types as tap_types
from app.specs import adminapi as spec

_ADMIN_TAP_SYNC_QUERY_TIMEOUT_SECONDS = 60


def _json_cell(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)


@final
class Actions(interface.Actions):
    def __init__(
        self,
        repo: repository.Repository,
        authenticator: auth.Authenticator,
        storage: postgres.PgStorage,
        clients: clients.Clients,
        table_stats_cache: cache.BackgroundCache[spec.TableStatsSnapshot],
    ):
        self._repo = repo
        self.source_manager = sources.SourceManager(repo)
        self.auth_manager = admin_auth.AuthManager(authenticator, storage)
        self.table_upload_manager = table_upload.TableUploadManager(
            repo,
            clients,
            table_stats_cache,
        )
        self.crossmatch_manager = crossmatch.CrossmatchManager(repo)
        self.pgc_manager = pgc.PgcManager(repo)
        self.layer1_writer = layer1_write.Layer1Writer(repo)
        self.catalog_manager = catalogs.CatalogManager(repo)

    def create_source(self, r: spec.CreateSourceRequest) -> spec.CreateSourceResponse:
        return self.source_manager.create_source(r)

    def login(self, r: spec.LoginRequest) -> spec.LoginResponse:
        return self.auth_manager.login(r)

    def logout(self, token: str) -> spec.LogoutResponse:
        return self.auth_manager.logout(token)

    def register(self, r: spec.RegisterRequest) -> spec.RegisterResponse:
        return self.auth_manager.register(r)

    def add_data(self, r: spec.AddDataRequest) -> spec.AddDataResponse:
        return self.table_upload_manager.add_data(r)

    def create_table(self, r: spec.CreateTableRequest) -> tuple[spec.CreateTableResponse, bool]:
        return self.table_upload_manager.create_table(r)

    def patch_table(self, r: spec.PatchTableRequest) -> spec.PatchTableResponse:
        return self.table_upload_manager.patch_table(r)

    def get_table(self, r: spec.GetTableRequest) -> spec.GetTableResponse:
        return self.table_upload_manager.get_table(r)

    def get_table_list(self, r: spec.GetTableListRequest) -> spec.GetTableListResponse:
        return self.table_upload_manager.get_table_list(r)

    def get_catalogs(self) -> spec.GetCatalogsResponse:
        return self.catalog_manager.get_catalogs()

    def get_records(self, r: spec.GetRecordsRequest) -> spec.GetRecordsResponse:
        return self.table_upload_manager.get_records(r)

    def get_record_crossmatch(self, r: spec.GetRecordCrossmatchRequest) -> spec.GetRecordCrossmatchResponse:
        return self.crossmatch_manager.get_record_crossmatch(r)

    def save_structured_data(self, r: spec.SaveStructuredDataRequest) -> spec.SaveStructuredDataResponse:
        return self.layer1_writer.save_data(r)

    def set_crossmatch_results(self, r: spec.SetCrossmatchResultsRequest) -> spec.SetCrossmatchResultsResponse:
        return self.crossmatch_manager.set_crossmatch_results(r)

    def assign_record_pgcs(self, r: spec.AssignRecordPgcsRequest) -> spec.AssignRecordPgcsResponse:
        return self.crossmatch_manager.assign_record_pgcs(r)

    def merge_pgcs(self, r: spec.MergePgcsRequest) -> spec.MergePgcsResponse:
        return self.pgc_manager.merge_pgcs(r)

    def tap_sync(self, request: spec.TAPSyncRequest) -> spec.TAPSyncResponse:
        result = self._repo.query_with_metadata(
            request.query,
            request.maxrec,
            timeout_seconds=_ADMIN_TAP_SYNC_QUERY_TIMEOUT_SECONDS,
        )
        columns: list[spec.TAPVOTableColumn] = []
        for col in result.columns:
            datatype = tap_types.python_to_tap_datatype(col.sample_value)
            columns.append(
                spec.TAPVOTableColumn(
                    name=col.column_name,
                    datatype=datatype,
                    arraysize="*" if datatype == "char" else None,
                )
            )
        data = [[_json_cell(cell) for cell in row] for row in result.rows]
        return spec.TAPSyncResponse(
            resource=spec.TAPVOTableResource(
                table=spec.TAPVOTableTable(columns=columns, data=data),
            )
        )
