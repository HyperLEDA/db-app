from typing import Any, final

import structlog
from psycopg.types import json

from app import entities
from app.data import template
from app.lib.storage import enums, postgres
from app.lib.web.errors import DatabaseError


@final
class CommonRepository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def create_bibliography(self, code: str, year: int, authors: list[str], title: str) -> int:
        result = self._storage.query_one(
            """
            INSERT INTO common.bib (code, year, author, title) 
            VALUES (%s, %s, %s, %s) 
            ON CONFLICT (code) DO UPDATE SET year = EXCLUDED.year, author = EXCLUDED.author, title = EXCLUDED.title
            RETURNING id 
            """,
            params=[code, year, authors, title],
        )

        if result is None:
            raise DatabaseError("no result returned from query")

        return int(result["id"])

    def get_source_entry(self, source_name: str) -> entities.Bibliography:
        row = self._storage.query_one(template.GET_SOURCE_BY_CODE, params=[source_name])

        return entities.Bibliography(**row)

    def get_source_by_id(self, source_id: int) -> entities.Bibliography:
        row = self._storage.query_one(template.GET_SOURCE_BY_ID, params=[source_id])

        return entities.Bibliography(**row)

    def insert_task(self, task: entities.Task) -> int:
        row = self._storage.query_one(
            "INSERT INTO common.tasks (task_name, payload) VALUES (%s, %s) RETURNING id",
            params=[task.task_name, json.Jsonb(task.payload)],
        )

        row_id = row.get("id")
        if row_id is None:
            raise DatabaseError("found row but it has no 'id' field")

        return int(row_id)

    def get_task_info(self, task_id: int) -> entities.Task:
        row = self._storage.query_one(template.GET_TASK_INFO, params=[task_id])

        return entities.Task(**row)

    def set_task_status(self, task_id: int, task_status: enums.TaskStatus) -> None:
        self._storage.exec(
            "UPDATE common.tasks SET status = %s WHERE id = %s",
            params=[task_status, task_id],
        )

    def fail_task(self, task_id: int, message: dict[str, Any]) -> None:
        self._storage.exec(
            "UPDATE common.tasks SET status = %s, message = %s WHERE id = %s",
            params=[enums.TaskStatus.FAILED, json.Jsonb(message), task_id],
        )
