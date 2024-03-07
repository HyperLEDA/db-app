from dataclasses import dataclass
from pathlib import Path

from marshmallow import Schema, fields, post_load
import yaml

from app.server import ServerConfig, ServerConfigSchema


@dataclass
class Config:
    server: ServerConfig


class ConfigSchema(Schema):
    server = fields.Nested(ServerConfigSchema, required=True)

    @post_load
    def make(self, data, **kwargs):
        return Config(**data)


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())
    return ConfigSchema().load(data)
