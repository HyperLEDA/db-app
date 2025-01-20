from dataclasses import dataclass

from marshmallow import Schema, fields, post_load


@dataclass
class ServerConfig:
    port: int
    host: str
    swagger_ui_path: str = "/api/docs"


class ServerConfigSchema(Schema):
    port = fields.Int(required=True)
    host = fields.Str(required=True)
    swagger_ui_path = fields.Str(required=False)

    @post_load
    def make(self, data, **kwargs):
        return ServerConfig(**data)
