from dataclasses import dataclass

import pydantic
from marshmallow import Schema, fields, post_load

from app.lib import config


class PgStorageConfigPydantic(config.ConfigSettings):
    endpoint: str
    port: int = pydantic.Field(validation_alias=pydantic.AliasChoices("STORAGE_PORT", "port"))
    dbname: str
    user: str
    password: str = pydantic.Field(validation_alias=pydantic.AliasChoices("STORAGE_PASSWORD", "password"))

    def get_dsn(self) -> str:
        # TODO: SSL and other options like transaction timeout
        return f"postgresql://{self.endpoint}:{self.port}/{self.dbname}?user={self.user}&password={self.password}"


@dataclass
class PgStorageConfig:
    endpoint: str
    port: int
    dbname: str
    user: str
    password: str

    def get_dsn(self) -> str:
        # TODO: SSL and other options like transaction timeout
        return f"postgresql://{self.endpoint}:{self.port}/{self.dbname}?user={self.user}&password={self.password}"


class PgStorageConfigSchema(Schema):
    endpoint = fields.Str(required=True)
    port = config.EnvField("STORAGE_PORT", fields.Int(required=True))
    dbname = fields.Str(required=True)
    user = fields.Str(required=True)
    password = config.EnvField("STORAGE_PASSWORD", fields.Str(required=True))

    @post_load
    def make(self, data, **kwargs):
        return PgStorageConfig(**data)
