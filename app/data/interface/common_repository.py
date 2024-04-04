import abc

import psycopg

from app.data import model
from app.data.interface import transactional


class CommonRepository(transactional.Transactional):
    @abc.abstractmethod
    def create_bibliography(self, bibliography: model.Bibliography, tx: psycopg.Transaction | None = None):
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_bibliography(self, bibliography_id: int, tx: psycopg.Transaction | None = None) -> model.Bibliography:
        raise NotImplementedError("not implemented")

    @abc.abstractmethod
    def get_bibliography_list(
        self, offset: int, limit: int, tx: psycopg.Transaction | None = None
    ) -> list[model.Bibliography]:
        raise NotImplementedError("not implemented")