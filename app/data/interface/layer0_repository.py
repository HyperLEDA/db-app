import abc

import psycopg

from app.data import model
from app.data.interface import transactional


class Layer0Repository(transactional.Transactional):
    @abc.abstractmethod
    def create_table(self, data: model.Layer0Creation, tx: psycopg.Transaction | None = None) -> str:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def insert_raw_data(self, data: model.Layer0RawData, tx: psycopg.Transaction | None = None) -> None:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def table_exists(self, schema: str, table_name: str) -> bool:
        raise NotImplementedError("not implemented")
