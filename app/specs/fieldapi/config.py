import pydantic_settings as settings

from app.lib import config


class FieldAPIConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="FIELDAPI_")

    base_url: str | None = None
    timeout_seconds: float = 10.0
