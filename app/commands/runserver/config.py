from dataclasses import dataclass, field
from pathlib import Path

import yaml
from marshmallow import Schema, fields, post_load

from app.lib import config
from app.lib.storage import postgres, redis
from app.lib.web import server


@dataclass
class ClientsConfig:
    ads_token: str = ""


class ClientsConfigSchema(Schema):
    ads_token = config.EnvField("ADS_TOKEN", fields.Str())

    @post_load
    def make(self, data, **kwargs):
        return ClientsConfig(**data)


@dataclass
class Config:
    server: server.ServerConfig
    storage: postgres.PgStorageConfig
    queue: redis.QueueConfig
    clients: ClientsConfig = field(default_factory=ClientsConfig)
    auth_enabled: bool = False


class ConfigSchema(Schema):
    server = fields.Nested(server.ServerConfigSchema(), required=True)
    storage = fields.Nested(postgres.PgStorageConfigSchema(), required=True)
    queue = fields.Nested(redis.QueueConfigSchema(), required=True)
    auth_enabled = fields.Bool(required=False)

    @post_load
    def make(self, data, **kwargs):
        return Config(**data)


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return ConfigSchema().load(data)
