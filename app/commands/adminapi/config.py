from pathlib import Path

import pydantic_settings as settings
import yaml

from app.lib import config
from app.lib.storage import postgres, redis
from app.lib.web import server


class ClientsConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="CLIENTS_")

    enabled: bool
    ads_token: str


class Config(config.ConfigSettings):
    server: server.ServerConfig
    storage: postgres.PgStorageConfig
    queue: redis.QueueConfig
    clients: ClientsConfig
    auth_enabled: bool


def parse_config(path: str) -> Config:
    data = yaml.safe_load(Path(path).read_text())

    return Config(**data)
