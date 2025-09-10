import pydantic_settings as settings


class BaseConfigSettings(settings.BaseSettings):
    pass


class ConfigSettings(BaseConfigSettings):
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
