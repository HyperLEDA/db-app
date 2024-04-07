from dataclasses import dataclass
from pathlib import Path

import yaml
from marshmallow import Schema, fields, post_load

from app.lib.storage import postgres, redis
from app.presentation.server import ServerConfig, ServerConfigSchema


@dataclass
class Config:
    server: ServerConfig
    storage: postgres.PgStorageConfig
    queue: redis.QueueConfig


class ConfigSchema(Schema):
    server = fields.Nested(ServerConfigSchema(), required=True)
    storage = fields.Nested(postgres.PgStorageConfigSchema(), required=True)
    queue = fields.Nested(redis.QueueConfigSchema(), required=True)

    @post_load
    def make(self, data, **kwargs):
        return Config(**data)


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    return ConfigSchema().load(data)
