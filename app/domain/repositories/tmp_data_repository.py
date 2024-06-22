from abc import ABC, abstractmethod
from typing import Any

from pandas import DataFrame

from app.domain.model.params import TmpDataRepositoryQueryParam


class TmpDataRepository(ABC):
    @abstractmethod
    async def make_table(self, data: DataFrame, index_on: list[str] | None) -> str:
        """
        Make a temporary table, and fill it with data
        :param data: Data to be put in the table
        :param index_on: Names of columns to build index on
        :return: Name of the created table
        """

    @abstractmethod
    async def query_table(self, param: TmpDataRepositoryQueryParam) -> list[dict[str, Any]]:
        """
        :param param: Query param, specifying table to query and query params
        :return: List of resulting rows
        """

    @abstractmethod
    async def drop_table(self, name: str):
        """
        Drop and destroy temporary table
        :param name: Table name
        """
