from typing import final

import psycopg

from app import data
from app.data import model, template


@final
class DataRespository(data.Repository):
    def __init__(self, storage: data.Storage):
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

        return [row.get("id") for row in rows]

    def create_designations(self, designations: list[model.Designation], tx: psycopg.Transaction | None = None):
        params = []
        for designation in designations:
            params.extend([designation.pgc, designation.design, designation.bib])

        self._storage.exec(template.NEW_DESIGNATIONS.render(objects=designations), params, tx)

    def get_designations(
        self, pgc: int, offset: int, limit: int, tx: psycopg.Transaction | None = None
    ) -> list[model.Designation]:
        rows = self._storage.query(template.GET_DESIGNATIONS, [pgc, offset, limit], tx)

        return [model.Designation(**row) for row in rows]

    def create_coordinates(self, coordinates: list[model.CoordinateData], tx: psycopg.Transaction | None = None):
        params = []
        for coordinate in coordinates:
            params.extend([coordinate.pgc, coordinate.ra, coordinate.dec, coordinate.bib])

        self._storage.exec(template.NEW_COORDINATES.render(objects=coordinates), params, tx)
