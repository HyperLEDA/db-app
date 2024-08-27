from abc import ABC, abstractmethod
from typing import Sequence

from pandas import DataFrame, Series


class NameDescr(ABC):
    """Describes, how to extract object names from table"""

    def parse_name(self, data: DataFrame) -> Sequence[tuple[str, list[str]] | Exception]:
        """
        Extract names from data
        :param data: Data table
        :return: For each row tuple of (main name, all names) or error if unable to parse name
        """
        return data.apply(self._parse_row, axis=1)

    @abstractmethod
    def _parse_row(self, data: Series) -> tuple[str, list[str]]:
        """
        Should be implemented for parsing
        :param data: Collection of values from table row, order is as specified in column_names in constructor
        :return: Parsed main name and all names
        """
