import http

from app.lib.web import server
from app.presentation.adminapi import (
    add_data,
    create_marking,
    create_source,
    create_table,
    get_api_v1_table_validation,
    get_table_metadata,
    get_task_info,
    interface,
    login,
    patch_api_v1_table,
    table_status_stats,
)


class Server(server.WebServer):
    def __init__(self, actions: interface.Actions, config: server.ServerConfig, *args, **kwargs):
        super().__init__(self.routes(actions), config, *args, **kwargs)

    @classmethod
    def routes(cls, actions: interface.Actions) -> list[server.Route]:
        return [
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/admin/api/v1/table/data",
                    add_data.AddDataRequestSchema,
                    add_data.AddDataResponseSchema,
                ),
                add_data.add_data_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/admin/api/v1/source",
                    create_source.CreateSourceRequestSchema,
                    create_source.CreateSourceResponseSchema,
                ),
                create_source.create_source_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/admin/api/v1/table",
                    create_table.CreateTableRequestSchema,
                    create_table.CreateTableResponseSchema,
                ),
                create_table.create_table_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/admin/api/v1/table/metadata",
                    get_table_metadata.GetTableMetadataRequestSchema,
                    get_table_metadata.GetTableMetadataResponseSchema,
                ),
                get_table_metadata.get_table_metadata_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/admin/api/v1/table/validation",
                    get_api_v1_table_validation.GetTableValidationRequestSchema,
                    get_api_v1_table_validation.GetTableValidationResponseSchema,
                ),
                get_api_v1_table_validation.get_table_validation_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.PATCH,
                    "/admin/api/v1/table",
                    patch_api_v1_table.PatchTableRequestSchema,
                    patch_api_v1_table.PatchTableResponseSchema,
                ),
                patch_api_v1_table.patch_table_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/admin/api/v1/task",
                    get_task_info.GetTaskInfoRequestSchema,
                    get_task_info.GetTaskInfoResponseSchema,
                ),
                get_task_info.get_task_info_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/admin/api/v1/login",
                    login.LoginRequestSchema,
                    login.LoginResponseSchema,
                ),
                login.login_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/admin/api/v1/table/status/stats",
                    table_status_stats.TableStatusStatsRequestSchema,
                    table_status_stats.TableStatusStatsResponseSchema,
                ),
                table_status_stats.table_status_stats,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/admin/api/v1/marking",
                    create_marking.CreateMarkingRequestSchema,
                    create_marking.CreateMarkingResponseSchema,
                ),
                create_marking.create_marking_handler,
            ),
        ]
