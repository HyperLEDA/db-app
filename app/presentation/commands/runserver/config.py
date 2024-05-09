import os
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
    cfg: Config = ConfigSchema().load(data)

    # TODO: find some less repetitive way to load these values
    if (server_port := os.getenv("SERVER_PORT")) is not None:
        cfg.server.port = int(server_port)

    if (storage_port := os.getenv("STORAGE_PORT")) is not None:
        cfg.storage.port = int(storage_port)

    if (storage_password := os.getenv("STORAGE_PASSWORD")) is not None:
        cfg.storage.password = storage_password

    if (queue_port := os.getenv("QUEUE_PORT")) is not None:
        cfg.queue.port = int(queue_port)

    return cfg
