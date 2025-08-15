import pydantic_settings as settings

from app.lib import config


class ServerConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="SERVER_")

    port: int
    host: str
    path_prefix: str = "/api"
