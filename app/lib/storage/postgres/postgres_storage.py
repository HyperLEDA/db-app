from dataclasses import dataclass
from typing import Any

import numpy as np
import psycopg
import structlog
from marshmallow import Schema, fields, post_load
from psycopg import adapt, rows
from psycopg.types import enum, numeric

from app.lib.exceptions import new_database_error, new_internal_error
from app.lib.queue.task_status import TaskStatus
from app.lib.storage.postgres import config
from app.lib.storage.postgres import transaction as storageutils

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
    (TaskStatus, "task_status"),
]


class PgStorage:
    def __init__(self, cfg: config.PgStorageConfig, logger: structlog.stdlib.BoundLogger) -> None:
        self._config = cfg
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
            type_info = enum.EnumInfo.fetch(self._connection, pg_type)
            if type_info is None:
                raise RuntimeError(f"Unable to find enum {pg_type} in DB")

            enum.register_enum(
                type_info,
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
            raise RuntimeError("Unable to execute query: connection to Postgres was not established")

        log.debug("SQL query", query=query.replace("\n", " "), args=params)

        cursor = self._connection.cursor()

        with storageutils.get_or_create_transaction(self._connection, tx):
            cursor.execute(query, params)

    def query(self, query: str, params: list[Any], tx: psycopg.Transaction | None = None) -> list[rows.DictRow]:
        if params is None:
            params = []
        if self._connection is None:
            raise RuntimeError("Unable to execute query: connection to Postgres was not established")

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
