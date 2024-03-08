from abc import ABC, abstractmethod
from typing import Sequence

from astropy.units import Quantity, Unit
from pandas import DataFrame, Series

from .exceptions import ColumnNotFoundException


class ValueDescr(ABC):
    """
    Class, used for parsing values of certain types. Including errors for this values
    """

    def __init__(self, ucd: str, column_name: str, units: str):
        """
        :param ucd: UCD key for this value. Used to map value to layer 1 data types
        :param column_name: Column in DataFrame to work with
        :param units: Unit string representation (e.g. 'km/s'), that will be processed by `astropy.units`
        """
        self._ucd: str = ucd
        self._column_name: str = column_name
        self._units: str = units

    @abstractmethod
    def parse_values(self, data: DataFrame) -> Sequence[Quantity]:
        pass

    @property
    def ucd(self):
        return self._ucd

    @ucd.getter
    def ucd(self) -> str:
        return self._ucd

    @property
    def column_name(self):
        return self._column_name

    @column_name.getter
    def column_name(self) -> str:
        return self._column_name

    @property
    def units(self):
        return self._units

    @column_name.getter
    def units(self) -> str:
        return self._units

    def _parse_column(self, data: DataFrame) -> Sequence:
        col: Series = data.get(self._column_name)
        unit = Unit(self.units)

        if col is None:
            raise ColumnNotFoundException([self._column_name])

        return col.apply(lambda el: el * unit)
