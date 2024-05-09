from dataclasses import dataclass

from marshmallow import Schema, fields, post_load


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
    port = fields.Int(required=True)
    dbname = fields.Str(required=True)
    user = fields.Str(required=True)
    password = fields.Str(required=True)

    @post_load
    def make(self, data, **kwargs):
        return PgStorageConfig(**data)
