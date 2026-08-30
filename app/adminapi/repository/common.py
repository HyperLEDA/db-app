from collections.abc import Sequence
from typing import final

import structlog

from app.adminapi import model
from app.adminapi.repository import sql
from app.lib.storage import postgres


def get_column_units(storage: postgres.PgStorage, schema: str, table: str) -> dict[str, str]:
    info = postgres.get_table_metadata(storage, schema, table)
    return {name: col.unit for name, col in info.columns.items() if col.unit}


def touch_pgcs(storage: postgres.PgStorage, pgc_ids: Sequence[int]) -> None:
    if not pgc_ids:
        return
    storage.exec(
        "UPDATE common.pgc SET modification_time = NOW() WHERE id = ANY(%s)",
        params=[list(pgc_ids)],
    )


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

        return int(result["id"])

    def get_source_entry(self, source_name: str) -> model.Bibliography:
        row = self._storage.query_one(sql.GET_SOURCE_BY_CODE, params=[source_name])

        return model.Bibliography(**row)

    def get_source_by_id(self, source_id: int) -> model.Bibliography:
        row = self._storage.query_one(sql.GET_SOURCE_BY_ID, params=[source_id])

        return model.Bibliography(**row)

    def register_pgcs(self, pgcs: list[int]) -> None:
        self._storage.execute_batch(
            "INSERT INTO common.pgc (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
            [[pgc] for pgc in pgcs],
        )

    def get_existing_pgcs(self, pgcs: list[int]) -> set[int]:
        if not pgcs:
            return set()

        rows = self._storage.query(
            "SELECT id FROM common.pgc WHERE id = ANY(%s)",
            params=[pgcs],
        )
        return {int(row["id"]) for row in rows}

    def touch_pgcs(self, pgc_ids: Sequence[int]) -> None:
        touch_pgcs(self._storage, pgc_ids)

    def get_table_metadata(self, schema_name: str, table_name: str) -> postgres.TableInfo:
        return postgres.get_table_metadata(self._storage, schema_name, table_name)

    def get_nature_object_types(self) -> list[dict]:
        return self._storage.query(
            "SELECT type_name, description FROM nature.object_type",
        )
