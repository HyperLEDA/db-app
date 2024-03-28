import abc
from typing import Any

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

    def create_table(
        self, schema: str, name: str, fields: list[tuple[str, str]], tx: psycopg.Transaction | None = None
    ):
        raise NotImplementedError("not implemented")

    def insert_raw_data(
        self, schema: str, table_name: str, raw_data: list[dict[str, Any]], tx: psycopg.Transaction | None = None
    ) -> None:
        raise NotImplementedError("not implemented")
