from dataclasses import dataclass
from typing import Any

import numpy as np
import psycopg
import structlog
from marshmallow import Schema, fields, post_load
from psycopg import adapt, rows
from psycopg.types import enum, numeric

from app.data.model.task import TaskStatus
from app.data.util import storage as storageutils
from app.lib.exceptions import new_database_error, new_internal_error

log: structlog.stdlib.BoundLogger = structlog.get_logger()


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


class NumpyFloatDumper(numeric.FloatDumper):
    def dump(self, obj: Any) -> bytes | bytearray | memoryview:
        return super().dump(float(obj))


class NumpyIntDumper(numeric.IntDumper):
    def dump(self, obj: Any) -> bytes | bytearray | memoryview:
        return super().dump(int(obj))


class TaskStatusLoader(adapt.Loader):
    def load(self, data: bytes | bytearray | memoryview) -> Any:
        status = data.decode("utf-8")
        return TaskStatus.load(status)


DEFAULT_DUMPERS = [
    (np.float16, NumpyFloatDumper),
    (np.float32, NumpyFloatDumper),
    (np.float64, NumpyFloatDumper),
    (np.int16, NumpyIntDumper),
    (np.int32, NumpyIntDumper),
    (np.int64, NumpyIntDumper),
]

DEFAULT_ENUMS = [
    (TaskStatus, "task_status"),
]


class PgStorage:
    def __init__(self, config: PgStorageConfig, logger: structlog.stdlib.BoundLogger) -> None:
        self._config = config
        self._connection: psycopg.Connection | None = None
        self._logger = logger

    def connect(self) -> None:
        self._connection = psycopg.connect(self._config.get_dsn(), row_factory=rows.dict_row, autocommit=True)
        if self._connection is None:
            raise new_internal_error("unable to create database connection")

        self._logger.debug("connecting to Postgres", endpoint=self._config.endpoint, port=self._config.port)

        for python_type, dumper in DEFAULT_DUMPERS:
            self._connection.adapters.register_dumper(python_type, dumper)

        for python_type, pg_type in DEFAULT_ENUMS:
            enum.register_enum(
                enum.EnumInfo.fetch(self._connection, pg_type),
                self._connection,
                python_type,
                mapping={m: m.value for m in python_type},
            )

    def with_tx(self) -> psycopg.Transaction:
        if self._connection is None:
            raise RuntimeError("did not connect to database")

        return self._connection.transaction()

    def disconnect(self) -> None:
        if self._connection is not None:
            self._logger.debug("disconnecting from Postgres", endpoint=self._config.endpoint, port=self._config.port)

            self._connection.close()

    def exec(self, query: str, params: list[Any], tx: psycopg.Transaction | None = None) -> None:
        if params is None:
            params = []
        if self._connection is None:
            raise RuntimeError("did not connect to database")

        log.debug("SQL query", query=query.replace("\n", " "), args=params)

        cursor = self._connection.cursor()

        with storageutils.get_or_create_transaction(self._connection, tx):
            cursor.execute(query, params)

    def query(self, query: str, params: list[Any], tx: psycopg.Transaction | None = None) -> list[rows.DictRow]:
        if params is None:
            params = []
        if self._connection is None:
            raise RuntimeError("did not connect to database")

        log.debug("SQL query", query=query.replace("\n", " "), args=params)

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
