import pydantic_settings as settings

from app.lib.config.marshmallow import EnvField

__all__ = ["EnvField"]


class ConfigSettings(settings.BaseSettings):
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[settings.BaseSettings],
        init_settings: settings.PydanticBaseSettingsSource,
        env_settings: settings.PydanticBaseSettingsSource,
        dotenv_settings: settings.PydanticBaseSettingsSource,
        file_secret_settings: settings.PydanticBaseSettingsSource,
    ) -> tuple[settings.PydanticBaseSettingsSource, ...]:
        return env_settings, init_settings
