from dataclasses import dataclass
from typing import final

import structlog

from app.data import model, template
from app.lib import concurrency
from app.lib.storage import postgres
from app.lib.web.errors import DatabaseError


@dataclass
class ColumnSchemaInfo:
    name: str
    description: str | None
    unit: str | None
    ucd: str | None


@dataclass
class TableSchemaInfo:
    table_description: str
    columns: list[ColumnSchemaInfo]


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

    def get_source_entry(self, source_name: str) -> model.Bibliography:
        row = self._storage.query_one(template.GET_SOURCE_BY_CODE, params=[source_name])

        return model.Bibliography(**row)

    def get_source_by_id(self, source_id: int) -> model.Bibliography:
        row = self._storage.query_one(template.GET_SOURCE_BY_ID, params=[source_id])

        return model.Bibliography(**row)

    def register_pgcs(self, pgcs: list[int]):
        self._storage.exec(
            f"INSERT INTO common.pgc (id) VALUES {','.join(['(%s)'] * len(pgcs))} ON CONFLICT (id) DO NOTHING",
            params=pgcs,
        )

    def get_schema(self, schema_name: str, table_name: str) -> TableSchemaInfo:
        errgr = concurrency.ErrorGroup()
        table_task = errgr.run(
            self._storage.query_one,
            "SELECT param FROM meta.table_info WHERE schema_name=%s AND table_name=%s",
            params=[schema_name, table_name],
        )
        column_task = errgr.run(
            self._storage.query,
            "SELECT column_name, param FROM meta.column_info WHERE schema_name=%s AND table_name=%s",
            params=[schema_name, table_name],
        )
        errgr.wait()

        table_row = table_task.result()
        table_description = ""
        if table_row is not None and table_row.get("param") is not None:
            param = table_row["param"]
            if isinstance(param, dict):
                table_description = param.get("description") or ""

        column_rows = column_task.result()
        columns = []
        for row in column_rows:
            param = row.get("param") or {}
            if not isinstance(param, dict):
                param = {}
            columns.append(
                ColumnSchemaInfo(
                    name=row["column_name"],
                    description=param.get("description"),
                    unit=param.get("unit"),
                    ucd=param.get("ucd"),
                )
            )
        return TableSchemaInfo(table_description=table_description, columns=columns)
