from typing import final

import psycopg
import structlog

from app.data import interface, model, postgres_storage, template


@final
class Layer1Repository(interface.Layer1Repository):
    def __init__(self, storage: postgres_storage.PgStorage, logger: structlog.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def with_tx(self) -> psycopg.Transaction:
        return self._storage.with_tx()

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
