from dataclasses import dataclass

from marshmallow import Schema, fields, post_load

from app.presentation.server.handlers import (
    add_data,
    create_source,
    create_table,
    debug_start_task,
    get_source,
    get_source_list,
    get_task_info,
    ping,
    search_catalogs,
    start_task,
)

HTTPMETHOD_GET = "GET"
HTTPMETHOD_POST = "POST"

SWAGGER_UI_URL = "/api/docs"


@dataclass
class ServerConfig:
    port: int
    host: str


class ServerConfigSchema(Schema):
    port = fields.Int(required=True)
    host = fields.Str(required=True)

    @post_load
    def make(self, data, **kwargs):
        return ServerConfig(**data)


routes = [
    (HTTPMETHOD_GET, "/ping", ping.description),
    (HTTPMETHOD_POST, "/api/v1/admin/source", create_source.description),
    (HTTPMETHOD_GET, "/api/v1/source/list", get_source_list.description),
    (HTTPMETHOD_GET, "/api/v1/source", get_source.description),
    (HTTPMETHOD_GET, "/api/v1/pipeline/catalogs", search_catalogs.description),
    (HTTPMETHOD_POST, "/api/v1/admin/task", start_task.description),
    (HTTPMETHOD_POST, "/api/v1/admin/debug/task", debug_start_task.description),
    (HTTPMETHOD_GET, "/api/v1/admin/task", get_task_info.description),
    (HTTPMETHOD_POST, "/api/v1/admin/table", create_table.description),
    (HTTPMETHOD_POST, "/api/v1/admin/table/data", add_data.description),
]
