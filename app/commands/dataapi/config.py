from pathlib import Path

import yaml

from app.lib import config
from app.lib.storage import postgres
from app.lib.web import server


class Config(config.ConfigSettings):
    server: server.ServerConfigPydantic
    storage: postgres.PgStorageConfigPydantic


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return Config(**data)
