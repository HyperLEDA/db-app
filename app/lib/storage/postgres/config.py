import pydantic_settings as settings

from app.lib import config


class PgStorageConfig(config.ConfigSettings):
    model_config = settings.SettingsConfigDict(env_prefix="STORAGE_")

    endpoint: str
    port: int
    dbname: str
    user: str
    password: str

    def get_dsn(self) -> str:
        # TODO: SSL and other options like transaction timeout
        return f"postgresql://{self.endpoint}:{self.port}/{self.dbname}?user={self.user}&password={self.password}"
