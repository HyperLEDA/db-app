from typing import final

from app import data
from app.data import template
from app.data.model import Bibliography


@final
class DataRespository(data.Repository):
    def __init__(self, storage: data.Storage):
        self._storage = storage

    def create_bibliography(self, bibliography: Bibliography) -> int:
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

    def get_bibliography(self, id: int) -> Bibliography:
        row = self._storage.query_one(template.QUERY_ONE_BIBLIOGRAPHY, [id])

        return Bibliography(**row)
