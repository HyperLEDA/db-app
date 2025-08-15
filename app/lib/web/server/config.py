from dataclasses import dataclass

import pydantic_settings as settings
from marshmallow import Schema, fields, post_load

from app.lib import config


class ServerConfigPydantic(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="SERVER_")

    port: int
    host: str
    path_prefix: str = "/api"


@dataclass
class ServerConfig:
    port: int
    host: str
    path_prefix: str = "/api"


class ServerConfigSchema(Schema):
    port = config.EnvField("SERVER_PORT", fields.Int(required=True))
    host = fields.Str(required=True)
    path_prefix = fields.Str(required=False)

    @post_load
    def make(self, data, **kwargs):
        return ServerConfig(**data)
