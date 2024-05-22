from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence, Union

from astropy.coordinates import SkyCoord
from pandas import DataFrame

from app.domain.model.layer0.values.exceptions import ColumnNotFoundException


class CoordinateDescr(ABC):
    """
    Class, responsible to parse coordinates of certain types
    """

    def __init__(self, *col_names: str):
        """
        :param col_names: Names of columns, used to make coordinates
        """
        self._col_names: list[str] = list(col_names)

    def parse_coordinates(self, data: DataFrame) -> Sequence[Union[SkyCoord, ValueError]]:
        try:
            col = data[self._col_names]
        except KeyError as e:
            raise ColumnNotFoundException(list(set(self._col_names) - set(data.columns.values)), cause=e) from e

        return col.apply(self.__parse_row, axis=1)

    def __parse_row(self, data: Iterable[Any]) -> Union[SkyCoord, ValueError]:
        """
        :param data: Collection of values from table row, order is as specified in column_names in constructor
        :return: Parsed coordinates or ValueError if parsing ended up in error
        """
        try:
            return self._parse_row(data)
        except ValueError as e:
            return e

    def arg_number(self, col_name: str) -> int | None:
        """
        Returns argument number in constructor, if the name was passed in constructor
        :param col_name: Column name
        :return: Argument number or none if column not present
        """
        try:
            return self._col_names.index(col_name)
        except ValueError:
            return None

    @abstractmethod
    def _parse_row(self, data: Iterable[Any]) -> SkyCoord:
        """
        Should be implemented for parsing
        :param data: Collection of values from table row, order is as specified in column_names in constructor
        :return: Parsed coordinates
        """

    @abstractmethod
    def description_id(self):
        """
        Resturn's id of this coordinate description (e.g 'icrs' for ICRS system)
        """
