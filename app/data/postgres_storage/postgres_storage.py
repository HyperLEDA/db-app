from dataclasses import dataclass
from typing import Any

import numpy as np
import psycopg
import structlog
from marshmallow import Schema, fields, post_load
from psycopg import rows
from psycopg.types import numeric

from app.data.util import storage as storageutils
from app.lib.exceptions import new_database_error, new_internal_error

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@dataclass
class StorageConfig:
    endpoint: str
    port: int
    dbname: str
    user: str
    password: str
    log_enabled: bool = True

    def get_dsn(self) -> str:
        # TODO: SSL and other options like transaction timeout
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


class NumpyFloatDumper(numeric.FloatDumper):
    def dump(self, obj: Any) -> bytes | bytearray | memoryview:
        return super().dump(float(obj))


class NumpyIntDumper(numeric.IntDumper):
    def dump(self, obj: Any) -> bytes | bytearray | memoryview:
        return super().dump(int(obj))


class Storage:
    def __init__(self, config: StorageConfig) -> None:
        self._config = config
        self._connection: psycopg.Connection | None = None

    def connect(self) -> None:
        self._connection = psycopg.connect(self._config.get_dsn(), row_factory=rows.dict_row, autocommit=True)
        if self._connection is None:
            raise new_internal_error("unable to create database connection")

        self._connection.adapters.register_dumper(np.float16, NumpyFloatDumper)
        self._connection.adapters.register_dumper(np.float32, NumpyFloatDumper)
        self._connection.adapters.register_dumper(np.float64, NumpyFloatDumper)
        self._connection.adapters.register_dumper(np.int16, NumpyIntDumper)
        self._connection.adapters.register_dumper(np.int32, NumpyIntDumper)
        self._connection.adapters.register_dumper(np.int64, NumpyIntDumper)

    def with_tx(self) -> psycopg.Transaction:
        if self._connection is None:
            raise RuntimeError("did not connect to database")

        return self._connection.transaction()

    def disconnect(self) -> None:
        if self._connection is not None:
            self._connection.close()

    def exec(self, query: str, params: list[Any], tx: psycopg.Transaction | None = None) -> None:
        if params is None:
            params = []
        if self._connection is None:
            raise RuntimeError("did not connect to database")

        if self._config.log_enabled:
            log.info("SQL query", query=query.replace("\n", " "), args=params)

        cursor = self._connection.cursor()

        with storageutils.get_or_create_transaction(self._connection, tx):
            cursor.execute(query, params)

    def query(self, query: str, params: list[Any], tx: psycopg.Transaction | None = None) -> list[rows.DictRow]:
        if params is None:
            params = []
        if self._connection is None:
            raise RuntimeError("did not connect to database")

        if self._config.log_enabled:
            log.info("SQL query", query=query.replace("\n", " "), args=params)

        cursor = self._connection.cursor()

        with storageutils.get_or_create_transaction(self._connection, tx):
            cursor.execute(query, params)
            result_rows = cursor.fetchall()

        return result_rows

    def query_one(self, query: str, params: list[Any], tx: psycopg.Transaction | None = None) -> rows.DictRow:
        result = self.query(query, params, tx)

        if len(result) < 1:
            raise new_database_error("was unable to fetch one value")

        return result[0]
