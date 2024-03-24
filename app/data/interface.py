import abc

import psycopg

from app.data import model


class Repository(abc.ABC):
    def with_tx(self) -> psycopg.Transaction:
        raise NotImplementedError("not implemented")

    def create_bibliography(self, bibliography: model.Bibliography, tx: psycopg.Transaction | None = None):
        raise NotImplementedError("not implemented")

    def get_bibliography(self, bibliography_id: int, tx: psycopg.Transaction | None = None) -> model.Bibliography:
        raise NotImplementedError("not implemented")

    def get_bibliography_list(
        self, offset: int, limit: int, tx: psycopg.Transaction | None = None
    ) -> list[model.Bibliography]:
        raise NotImplementedError("not implemented")

    def create_objects(self, n: int, tx: psycopg.Transaction | None = None) -> list[int]:
        raise NotImplementedError("not implemented")

    def create_designations(self, designations: list[model.Designation], tx: psycopg.Transaction | None = None):
        raise NotImplementedError("not implemented")

    def get_designations(
        self, pgc: int, offset: int, limit: int, tx: psycopg.Transaction | None = None
    ) -> list[model.Designation]:
        raise NotImplementedError("not implemented")

    def create_coordinates(self, coordinates: list[model.CoordinateData], tx: psycopg.Transaction | None = None):
        raise NotImplementedError("not implemented")
