from typing import Any, final

import psycopg
import structlog
from psycopg.types import json

from app.data import interface, model, template
from app.lib.exceptions import DatabaseError
from app.lib.storage import enums, postgres


@final
class CommonRepository(interface.CommonRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def with_tx(self) -> psycopg.Transaction:
        return self._storage.with_tx()

    def create_bibliography(
        self, code: str, year: int, authors: list[str], title: str, tx: psycopg.Transaction | None = None
    ) -> int:
        result = self._storage.query_one(
            """
            INSERT INTO common.bib (code, year, author, title) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (code) DO UPDATE SET year = EXCLUDED.year, author = EXCLUDED.author, title = EXCLUDED.title
            RETURNING id 
            """,
            params=[code, year, authors, title],
            tx=tx,
        )

        if result is None:
            raise DatabaseError("no result returned from query")

        return int(result.get("id"))

    def get_source_entry(self, source_name: str, tx: psycopg.Transaction | None = None) -> model.Bibliography:
        row = self._storage.query_one(template.GET_SOURCE_BY_CODE, params=[source_name], tx=tx)

        return model.Bibliography(**row)

    def get_source_by_id(self, source_id: int, tx: psycopg.Transaction | None = None) -> model.Bibliography:
        row = self._storage.query_one(template.GET_SOURCE_BY_ID, params=[source_id], tx=tx)

        return model.Bibliography(**row)

    def insert_task(self, task: model.Task, tx: psycopg.Transaction | None = None) -> int:
        row = self._storage.query_one(
            "INSERT INTO common.tasks (task_name, payload) VALUES (%s, %s) RETURNING id",
            params=[task.task_name, json.Jsonb(task.payload)],
            tx=tx,
        )

        row_id = row.get("id")
        if row_id is None:
            raise DatabaseError("found row but it has no 'id' field")

        return int(row_id)

    def get_task_info(self, task_id: int, tx: psycopg.Transaction | None = None) -> model.Task:
        row = self._storage.query_one(template.GET_TASK_INFO, params=[task_id], tx=tx)

        return model.Task(**row)

    def set_task_status(
        self,
        task_id: int,
        task_status: enums.TaskStatus,
        tx: psycopg.Transaction | None = None,
    ) -> None:
        self._storage.exec(
            "UPDATE common.tasks SET status = %s WHERE id = %s",
            params=[task_status, task_id],
            tx=tx,
        )

    def fail_task(
        self,
        task_id: int,
        message: dict[str, Any],
        tx: psycopg.Transaction | None = None,
    ) -> None:
        self._storage.exec(
            "UPDATE common.tasks SET status = %s, message = %s WHERE id = %s",
            params=[enums.TaskStatus.FAILED, json.Jsonb(message), task_id],
            tx=tx,
        )
