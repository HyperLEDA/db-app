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

    def get_bibliography(self, id: int) -> model.Bibliography:
        row = self._storage.query_one(template.QUERY_ONE_BIBLIOGRAPHY, [id])

        return model.Bibliography(**row)

    def get_bibliography_list(self, offset: int, limit: int) -> list[model.Bibliography]:
        rows = self._storage.query(
            template.QUERY_BIBLIOGRAPHY_TEMPLATE.render(offset=offset, limit=limit),
        )

        return [model.Bibliography(**row) for row in rows]
