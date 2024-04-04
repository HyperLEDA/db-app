import abc

import psycopg

from app.data import model
from app.data.interface import transactional


class Layer1Repository(transactional.Transactional):
    @abc.abstractmethod
    def create_objects(self, n: int, tx: psycopg.Transaction | None = None) -> list[int]:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def create_designations(self, designations: list[model.Designation], tx: psycopg.Transaction | None = None):
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_designations(
        self, pgc: int, offset: int, limit: int, tx: psycopg.Transaction | None = None
    ) -> list[model.Designation]:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def create_coordinates(self, coordinates: list[model.CoordinateData], tx: psycopg.Transaction | None = None):
        raise NotImplementedError("not implemented")
