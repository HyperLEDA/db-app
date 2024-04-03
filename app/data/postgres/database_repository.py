from typing import Any, final

import psycopg
import structlog

from app import data
from app.data import model, template
from app.data.postgres import postgres_storage

log: structlog.stdlib.BoundLogger = structlog.get_logger()


@final
class DataRepository(data.DatabaseRepository):
    def __init__(self, storage: postgres_storage.Storage) -> None:
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

    def create_objects(self, n: int, tx: psycopg.Transaction | None = None) -> list[int]:
        query = template.NEW_OBJECTS.render(n=n)
        rows = self._storage.query(query, [], tx)

        return [int(row.get("id")) for row in rows]

    def create_designations(self, designations: list[model.Designation], tx: psycopg.Transaction | None = None) -> None:
        params = []
        for designation in designations:
            params.extend([designation.pgc, designation.design, designation.bib])

        self._storage.exec(template.NEW_DESIGNATIONS.render(objects=designations), params, tx)

    def get_designations(
        self, pgc: int, offset: int, limit: int, tx: psycopg.Transaction | None = None
    ) -> list[model.Designation]:
        rows = self._storage.query(template.GET_DESIGNATIONS, [pgc, offset, limit], tx)

        return [model.Designation(**row) for row in rows]

    def create_coordinates(
        self, coordinates: list[model.CoordinateData], tx: psycopg.Transaction | None = None
    ) -> None:
        params = []
        for coordinate in coordinates:
            params.extend([coordinate.pgc, coordinate.ra, coordinate.dec, coordinate.bib])

        self._storage.exec(template.NEW_COORDINATES.render(objects=coordinates), params, tx)

    def create_table(
        self,
        schema: str,
        name: str,
        fields: list[tuple[str, str]],
        tx: psycopg.Transaction | None = None,
    ) -> None:
        self._storage.exec(
            template.CREATE_TABLE.render(
                schema=schema,
                name=name,
                fields=fields,
            ),
            [],
            tx,
        )

    def insert_raw_data(
        self, schema: str, table_name: str, raw_data: list[dict[str, Any]], tx: psycopg.Transaction | None = None
    ) -> None:
        """
        This method puts everything in parameters for prepared statement. This should not be a big
        issue but one would be better off using this function in batches since prepared statement make
        this quite cheap (excluding network slow down, though).

        Also the contract of this method requires all dicts to have the same set of keys.
        """
        if not raw_data:
            log.warn("trying to insert 0 rows into the table", table=f"{schema}.{table_name}")
            return

        params = []
        objects = []
        fields = raw_data[0].keys()

        for row in raw_data:
            obj = {}
            for field in fields:
                value = row[field]
                try:
                    params.append(value.item())
                except AttributeError:
                    params.append(value)
                obj[field] = "%s"

            objects.append(obj)

        query = template.INSERT_RAW_DATA.render(schema=schema, table=table_name, fields=fields, objects=objects)

        self._storage.exec(
            query,
            params,
            tx,
        )
