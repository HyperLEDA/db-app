from typing import final

import psycopg
import structlog

from app.data import interface, model, postgres_storage, template


@final
class CommonRepository(interface.CommonRepository):
    def __init__(self, storage: postgres_storage.Storage, logger: structlog.BoundLogger) -> None:
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