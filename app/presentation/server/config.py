from dataclasses import dataclass

from marshmallow import Schema, fields, post_load

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
