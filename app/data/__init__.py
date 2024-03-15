from dataclasses import dataclass
from typing import Any

import psycopg2
from marshmallow import Schema, fields, post_load


@dataclass
class StorageConfig:
    endpoint: str
    port: int
    dbname: str
    user: str
    password: str

    def get_dsn(self) -> str:
        return f"postgresql://{self.endpoint}:{self.port}/{self.dbname}?user={self.user}&password={self.password}"


class StorageConfigSchema(Schema):
    endpoint = fields.Str(required=True)
    port = fields.Int(required=True)
    dbname = fields.Str(required=True)
    user = fields.Str(required=True)
    password = fields.Str(required=True)

    @post_load
    def make(self, data, **kwargs):
        return StorageConfig(**data)


class Storage:
    def __init__(self, config: StorageConfig):
        self.config = config
        self.connection = None

    def connect(self):
        self.connection = psycopg2.connect(self.config.get_dsn())

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()

    def exec(self, query: str, params: list[Any]):
        if self.connection is None:
            raise RuntimeError("did not connect to database")

        cursor = self.connection.cursor()
        cursor.execute(query, params)
        self.connection.commit()
        cursor.close()
