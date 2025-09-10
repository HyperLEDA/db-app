import pydantic_settings as settings

from app.lib import config


class QueueConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="QUEUE_")

    endpoint: str
    port: int
    queue_name: str
