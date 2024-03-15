from typing import final

from app import data
from app.data.model import Bibliography


@final
class DataRespository(data.Repository):
    def __init__(self, storage: data.Storage):
        self._storage = storage

    def create_bibliography(self, bibliography: Bibliography):
        self._storage.exec(
            "INSERT INTO common.bib (bibcode, year, author, title) VALUES (%s, %s, %s, %s)",
            [
                bibliography.bibcode,
                bibliography.year,
                bibliography.author,
                bibliography.title,
            ],
        )

    def get_bibliography(self) -> Bibliography:
        pass
