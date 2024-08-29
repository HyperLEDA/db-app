import abc

import psycopg

from app import entities
from app.data.interface import transactional


class Layer0Repository(transactional.Transactional):
    @abc.abstractmethod
    def create_table(
        self, data: entities.Layer0Creation, tx: psycopg.Transaction | None = None
    ) -> entities.Layer0CreationResponse:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def insert_raw_data(self, data: entities.Layer0RawData, tx: psycopg.Transaction | None = None) -> None:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_table_id(self, table_name: str) -> tuple[int, bool]:
        raise NotImplementedError("not implemented")
