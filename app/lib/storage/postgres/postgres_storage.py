from collections.abc import Sequence
from typing import Any

import numpy as np
import psycopg
import structlog
from psycopg import rows
from psycopg.types import enum, numeric

from app.lib.storage import enums
from app.lib.storage.postgres import config
from app.lib.web.errors import DatabaseError, InternalError

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class NumpyFloatDumper(numeric.FloatDumper):
    def dump(self, obj: Any) -> bytes | bytearray | memoryview:
        return super().dump(float(obj))


class NumpyIntDumper(numeric.IntDumper):
    def dump(self, obj: Any) -> bytes | bytearray | memoryview:
        return super().dump(int(obj))


DEFAULT_DUMPERS: list[tuple[type, type]] = [
    (np.float16, NumpyFloatDumper),
    (np.float32, NumpyFloatDumper),
    (np.float64, NumpyFloatDumper),
    (np.int16, NumpyIntDumper),
    (np.int32, NumpyIntDumper),
    (np.int64, NumpyIntDumper),
]

DEFAULT_ENUMS = [
    (enums.TaskStatus, "common.task_status"),
    (enums.DataType, "common.datatype"),
    (enums.RawDataStatus, "rawdata.status"),
    (enums.ObjectCrossmatchStatus, "rawdata.crossmatch_status"),
]


class PgStorage:
    def __init__(self, cfg: config.PgStorageConfig, logger: structlog.stdlib.BoundLogger) -> None:
        self._config = cfg
        self._connection: psycopg.Connection | None = None
        self._logger = logger

    def get_config(self) -> config.PgStorageConfig:
        return self._config

    def connect(self) -> None:
        self._connection = psycopg.connect(self._config.get_dsn(), row_factory=rows.dict_row, autocommit=True)
        if self._connection is None:
            raise InternalError("unable to create database connection")

        self._logger.debug("connecting to Postgres", endpoint=self._config.endpoint, port=self._config.port)

        for python_type, dumper in DEFAULT_DUMPERS:
            self._connection.adapters.register_dumper(python_type, dumper)

        for python_type, pg_type in DEFAULT_ENUMS:
            self.register_type(python_type, pg_type)

    def register_type(self, enum_type: type[enum.Enum], pg_type: str) -> None:
        if self._connection is None:
            raise RuntimeError("did not connect to database")

        type_info = enum.EnumInfo.fetch(self._connection, pg_type)
        if type_info is None:
            raise RuntimeError(f"Unable to find enum {pg_type} in DB")

        enum.register_enum(
            type_info,
            self._connection,
            enum_type,
            mapping={m: m.value for m in enum_type},
        )

    def get_connection(self) -> psycopg.Connection:
        if self._connection is None:
            raise InternalError("unable to create database connection")

        return self._connection

    def disconnect(self) -> None:
        if self._connection is not None:
            self._logger.debug("disconnecting from Postgres", endpoint=self._config.endpoint, port=self._config.port)

            self._connection.close()

    def exec(self, query: str, *, params: list[Any] | None = None) -> None:
        if params is None:
            params = []
        if self._connection is None:
            raise RuntimeError("Unable to execute query: connection to Postgres was not established")

        log.debug("SQL query", query=query.replace("\n", " "), args=params)

        cursor = self._connection.cursor()
        cursor.execute(query, params)

    def execute_many(self, query: str, params: Sequence[Sequence[Any]]):
        if self._connection is None:
            raise RuntimeError("Unable to execute query: connection to Postgres was not established")

        log.debug("SQL many", query=query.replace("\n", " "), args=params)

        cursor = self._connection.cursor()

        try:
            cursor.executemany(query, params)
        except psycopg.Error as e:
            raise DatabaseError(f"{type(e).__name__}: {str(e)}") from e

    def query(self, query: str, *, params: list[Any] | None = None) -> list[rows.DictRow]:
        if params is None:
            params = []
        if self._connection is None:
            raise RuntimeError("Unable to execute query: connection to Postgres was not established")

        log.debug("SQL query", query=query.replace("\n", " "), args=params)

        cursor = self._connection.cursor()
        cursor.execute(query, params)

        result = cursor.fetchall()
        log.debug("SQL result", num_rows=len(result))

        return result

    def query_one(self, query: str, *, params: list[Any] | None = None) -> rows.DictRow:
        result = self.query(query, params=params)

        if len(result) != 1:
            raise RuntimeError(f"was unable to fetch one value, got {len(result)} values")

        return result[0]
