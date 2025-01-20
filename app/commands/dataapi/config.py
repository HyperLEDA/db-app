from dataclasses import dataclass
from pathlib import Path

import yaml
from marshmallow import Schema, fields, post_load

from app.lib.storage import postgres
from app.lib.web import server


@dataclass
class Config:
    server: server.ServerConfig
    storage: postgres.PgStorageConfig


class ConfigSchema(Schema):
    server = fields.Nested(server.ServerConfigSchema(), required=True)
    storage = fields.Nested(postgres.PgStorageConfigSchema(), required=True)

    @post_load
    def make(self, data, **kwargs):
        return Config(**data)


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return ConfigSchema().load(data)
