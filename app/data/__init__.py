from dataclasses import dataclass
from typing import Any

import psycopg2
import structlog
from marshmallow import Schema, fields, post_load
from psycopg2 import extras

from app.data.interface import Repository
from app.lib.exceptions import new_database_error


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
        self.logger = structlog.get_logger()

    def connect(self):
        self.connection = psycopg2.connect(self.config.get_dsn())

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()

    def query(self, query: str, params: list[Any]) -> list[dict[str, Any]]:
        if self.connection is None:
            raise RuntimeError("did not connect to database")

        self.logger.info("SQL query", query=query.replace("\n", " "), args=params)

        cursor = self.connection.cursor(cursor_factory=extras.DictCursor)
        try:
            cursor.execute(query, params)
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e

        rows = cursor.fetchall()
        cursor.close()

        return rows

    def query_one(self, query: str, params: list[Any]) -> dict[str, Any]:
        result = self.query(query, params)

        if len(result) < 1:
            raise new_database_error("was unable to fetch one value")

        return result[0]
