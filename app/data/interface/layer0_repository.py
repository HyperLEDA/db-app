import abc
from typing import Any

import psycopg

from app.data.interface import transactional


class Layer0Repository(transactional.Transactional):
    @abc.abstractmethod
    def create_table(
        self, schema: str, name: str, fields: list[tuple[str, str]], tx: psycopg.Transaction | None = None
    ):
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def insert_raw_data(
        self, schema: str, table_name: str, raw_data: list[dict[str, Any]], tx: psycopg.Transaction | None = None
    ) -> None:
        raise NotImplementedError("not implemented")
