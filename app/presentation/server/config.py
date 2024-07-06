from dataclasses import dataclass

from marshmallow import Schema, fields, post_load

SWAGGER_UI_URL = "/api/docs"


@dataclass
class ServerConfig:
    port: int
    host: str
    auth_enabled: bool = False


class ServerConfigSchema(Schema):
    port = fields.Int(required=True)
    host = fields.Str(required=True)
    auth_enabled = fields.Bool(required=False)

    @post_load
    def make(self, data, **kwargs):
        return ServerConfig(**data)
