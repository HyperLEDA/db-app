import threading
import time
from collections.abc import Sequence
from typing import Any

import numpy as np
import psycopg
import structlog
from psycopg import rows, sql
from psycopg.types import enum, numeric
from psycopg_pool import ConnectionPool

from app.lib.storage import enums
from app.lib.storage.postgres import config
from app.lib.web.errors import InternalError

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

DEFAULT_ENUMS: list[tuple[type[enum.Enum], str]] = [
    (enums.DataType, "common.datatype"),
    (enums.RecordTriageStatus, "layer0.triage_status"),
]


class PgStorage:
    def __init__(self, cfg: config.PgStorageConfig, logger: structlog.stdlib.BoundLogger) -> None:
        self._config = cfg
        self._pool: ConnectionPool | None = None
        self._logger = logger
        self._local = threading.local()
        self._extra_enums: list[tuple[type[enum.Enum], str]] = []

    def _configure_connection(self, conn: psycopg.Connection) -> None:
        for python_type, dumper in DEFAULT_DUMPERS:
            conn.adapters.register_dumper(python_type, dumper)
        for enum_type, pg_type in DEFAULT_ENUMS + self._extra_enums:
            type_info = enum.EnumInfo.fetch(conn, pg_type)
            if type_info is None:
                raise RuntimeError(f"Unable to find enum {pg_type} in DB")
            enum.register_enum(
                type_info,
                conn,
                enum_type,
                mapping={m: m.value for m in enum_type},
            )

    def connect(self) -> None:
        self._logger.debug("connecting to Postgres", endpoint=self._config.endpoint, port=self._config.port)
        self._pool = ConnectionPool(
            self._config.get_dsn(),
            min_size=10,
            max_size=30,
            kwargs={"row_factory": rows.dict_row, "autocommit": True},
            configure=self._configure_connection,
        )

    def register_type(self, enum_type: type[enum.Enum], pg_type: str) -> None:
        self._extra_enums.append((enum_type, pg_type))

    def get_thread_conn(self) -> psycopg.Connection | None:
        return getattr(self._local, "conn", None)

    def set_thread_conn(self, conn: psycopg.Connection | None) -> None:
        self._local.conn = conn

    def get_pool(self) -> ConnectionPool:
        if self._pool is None:
            raise InternalError("connection pool is not initialized")
        return self._pool

    def get_connection(self) -> psycopg.Connection:
        conn = self.get_thread_conn()
        if conn is not None:
            return conn
        raise InternalError("no active transaction connection on this thread")

    def disconnect(self) -> None:
        if self._pool is not None:
            self._logger.debug("disconnecting from Postgres", endpoint=self._config.endpoint, port=self._config.port)
            self._pool.close()

    def query_str(self, query: str | sql.SQL | sql.Composed) -> str:
        if isinstance(query, str):
            return query
        conn = self.get_thread_conn()
        if conn is not None:
            return query.as_string(conn)
        with self.get_pool().connection() as c:
            return query.as_string(c)

    def exec(self, query: str | sql.SQL | sql.Composed, *, params: list[Any] | None = None) -> None:
        if params is None:
            params = []

        log.debug("SQL query", query=self.query_str(query).replace("\n", " "), args=params)

        conn = self.get_thread_conn()
        if conn is not None:
            conn.cursor().execute(query, params)
        else:
            with self.get_pool().connection() as c:
                c.cursor().execute(query, params)

    def execute_batch(self, query: str, rows_data: Sequence[Sequence[Any]]) -> int:
        log.debug("SQL execute batch", query=query.replace("\n", " "), num_rows=len(rows_data))

        if not rows_data:
            return 0

        conn = self.get_thread_conn()
        if conn is not None:
            cur = conn.cursor()
            cur.executemany(query, rows_data)
            return cur.rowcount

        with self.get_pool().connection() as c:
            cur = c.cursor()
            cur.executemany(query, rows_data)
            return cur.rowcount

    def query(self, query: str | sql.SQL | sql.Composed, *, params: list[Any] | None = None) -> list[rows.DictRow]:
        if params is None:
            params = []

        log.debug("SQL query", query=self.query_str(query).replace("\n", " "), args=params)

        def _run(conn: psycopg.Connection) -> list[rows.DictRow]:
            cursor = conn.cursor()
            start = time.monotonic()
            cursor.execute(query, params)
            result = cursor.fetchall()
            elapsed = time.monotonic() - start
            log.debug("SQL result", num_rows=len(result), elapsed_seconds=round(elapsed, 4))
            return result

        conn = self.get_thread_conn()
        if conn is not None:
            return _run(conn)
        with self.get_pool().connection() as c:
            return _run(c)

    def query_one(self, query: str | sql.SQL | sql.Composed, *, params: list[Any] | None = None) -> rows.DictRow:
        result = self.query(query, params=params)

        if len(result) != 1:
            raise RuntimeError(f"was unable to fetch one value, got {len(result)} values")

        return result[0]
