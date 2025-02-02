import http

from app.lib.web import server
from app.presentation.adminapi import (
    add_data,
    create_source,
    create_table,
    get_task_info,
    interface,
    login,
    set_table_status,
    table_process,
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
                    "/api/v1/admin/table/data",
                    add_data.AddDataRequestSchema,
                    add_data.AddDataResponseSchema,
                ),
                add_data.add_data_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/api/v1/admin/source",
                    create_source.CreateSourceRequestSchema,
                    create_source.CreateSourceResponseSchema,
                ),
                create_source.create_source_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/api/v1/admin/table",
                    create_table.CreateTableRequestSchema,
                    create_table.CreateTableResponseSchema,
                ),
                create_table.create_table_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/api/v1/admin/task",
                    get_task_info.GetTaskInfoRequestSchema,
                    get_task_info.GetTaskInfoResponseSchema,
                ),
                get_task_info.get_task_info_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/api/v1/login",
                    login.LoginRequestSchema,
                    login.LoginResponseSchema,
                ),
                login.login_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/api/v1/admin/table/status",
                    set_table_status.SetTableStatusRequestSchema,
                    set_table_status.SetTableStatusResponseSchema,
                ),
                set_table_status.set_table_status_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.POST,
                    "/api/v1/admin/table/process",
                    table_process.TableProcessRequestSchema,
                    table_process.TableProcessResponseSchema,
                ),
                table_process.table_process_handler,
            ),
            server.ActionRoute(
                actions,
                server.RouteInfo(
                    http.HTTPMethod.GET,
                    "/api/v1/table/status/stats",
                    table_status_stats.TableStatusStatsRequestSchema,
                    table_status_stats.TableStatusStatsResponseSchema,
                ),
                table_status_stats.table_status_stats,
            ),
        ]
