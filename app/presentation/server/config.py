from dataclasses import dataclass

from marshmallow import Schema, fields, post_load

from app.presentation.server import handlers

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
    (HTTPMETHOD_GET, "/ping", handlers.ping_handler),
    (HTTPMETHOD_POST, "/api/v1/admin/source", handlers.create_source_handler),
    (HTTPMETHOD_GET, "/api/v1/source", handlers.get_source_handler),
    (HTTPMETHOD_GET, "/api/v1/source/list", handlers.get_source_list_handler),
    (HTTPMETHOD_POST, "/api/v1/admin/object/batch", handlers.create_objects_handler),
    (HTTPMETHOD_POST, "/api/v1/admin/object", handlers.create_object_handler),
    (HTTPMETHOD_GET, "/api/v1/object/names", handlers.get_object_names_handler),
    (HTTPMETHOD_GET, "/api/v1/pipeline/catalogs", handlers.search_catalogs_handler),
    (HTTPMETHOD_POST, "/api/v1/task", handlers.start_task_handler),
    (HTTPMETHOD_POST, "/api/v1/debug/task", handlers.debug_start_task_handler),
    (HTTPMETHOD_GET, "/api/v1/task", handlers.get_task_info_handler),
]
