from dataclasses import dataclass
from pathlib import Path

import yaml
from marshmallow import Schema, fields, post_load

from app.data.repositories import QueueConfig
from app.data.repositories.queue_repository import QueueConfigSchema
from app.lib.storage.postgres import PgStorageConfig, PgStorageConfigSchema
from app.presentation.server import ServerConfig, ServerConfigSchema


@dataclass
class Config:
    server: ServerConfig
    storage: PgStorageConfig
    queue: QueueConfig


class ConfigSchema(Schema):
    server = fields.Nested(ServerConfigSchema(), required=True)
    storage = fields.Nested(PgStorageConfigSchema(), required=True)
    queue = fields.Nested(QueueConfigSchema(), required=True)

    @post_load
    def make(self, data, **kwargs):
        return Config(**data)


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    return ConfigSchema().load(data)
