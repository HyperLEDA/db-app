from typing import final

from app import data
from app.data import model, template


@final
class DataRespository(data.Repository):
    def __init__(self, storage: data.Storage):
        self._storage = storage

    def create_bibliography(self, bibliography: model.Bibliography) -> int | None:
        result = self._storage.query_one(
            "INSERT INTO common.bib (bibcode, year, author, title) VALUES (%s, %s, %s, %s) RETURNING id",
            [
                bibliography.bibcode,
                bibliography.year,
                bibliography.author,
                bibliography.title,
            ],
        )

        return result.get("id")

    def get_bibliography(self, bibliography_id: int) -> model.Bibliography:
        row = self._storage.query_one(template.ONE_BIBLIOGRAPHY, [bibliography_id])

        return model.Bibliography(**row)

    def get_bibliography_list(self, offset: int, limit: int) -> list[model.Bibliography]:
        rows = self._storage.query(template.BIBLIOGRAPHY_TEMPLATE, [offset, limit])

        return [model.Bibliography(**row) for row in rows]

    def create_objects(self, n: int) -> list[int]:
        rows = self._storage.query(template.NEW_OBJECTS.render(n=n))

        return [row.get("id") for row in rows]

    def create_designations(self, designations: list[model.Designation]):
        params = []
        for designation in designations:
            params.extend([designation.pgc, designation.design, designation.bib])

        self._storage.exec(template.NEW_DESIGNATIONS.render(objects=designations), params)

    def get_designations(self, pgc: int, offset: int, limit: int) -> list[model.Designation]:
        rows = self._storage.query(template.GET_DESIGNATIONS, [pgc, offset, limit])

        return [model.Designation(**row) for row in rows]

    def create_coordinates(self, coordinates: list[model.CoordinateData]):
        params = []
        for coordinate in coordinates:
            params.extend([coordinate.pgc, coordinate.ra, coordinate.dec, coordinate.bib])

        self._storage.exec(template.NEW_COORDINATES.render(objects=coordinates), params)
