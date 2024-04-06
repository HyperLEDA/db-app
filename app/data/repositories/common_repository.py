from typing import final

import psycopg
import structlog
from psycopg.types import json

from app.data import interface, model, template
from app.lib.storage import postgres


@final
class CommonRepository(interface.CommonRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def with_tx(self) -> psycopg.Transaction:
        return self._storage.with_tx()

    def create_bibliography(
        self, bibliography: model.Bibliography, tx: psycopg.Transaction | None = None
    ) -> int | None:
        result = self._storage.query_one(
            "INSERT INTO common.bib (bibcode, year, author, title) VALUES (%s, %s, %s, %s) RETURNING id",
            [
                bibliography.bibcode,
                bibliography.year,
                bibliography.author,
                bibliography.title,
            ],
            tx,
        )

        return result.get("id")

    def get_bibliography(self, bibliography_id: int, tx: psycopg.Transaction | None = None) -> model.Bibliography:
        row = self._storage.query_one(template.ONE_BIBLIOGRAPHY, [bibliography_id], tx)

        return model.Bibliography(**row)

    def get_bibliography_list(
        self, offset: int, limit: int, tx: psycopg.Transaction | None = None
    ) -> list[model.Bibliography]:
        rows = self._storage.query(template.BIBLIOGRAPHY_TEMPLATE, [offset, limit], tx)

        return [model.Bibliography(**row) for row in rows]

    def insert_task(self, task: model.Task, tx: psycopg.Transaction | None = None) -> int:
        row = self._storage.query_one(
            "INSERT INTO common.tasks (task_name, payload) VALUES (%s, %s) RETURNING id",
            [task.task_name, json.Jsonb(task.payload)],
            tx,
        )

        return row.get("id")

    def get_task_info(
        self,
        task_id: int,
        tx: psycopg.Transaction | None = None,
    ) -> model.Task:
        row = self._storage.query_one(
            "SELECT id, task_name, payload, user_id, status, start_time, end_time FROM common.tasks WHERE id = %s",
            [task_id],
            tx,
        )

        return model.Task(**row)
