from astropy.units import Quantity
from pandas import DataFrame, Series

from .value_descr import ValueDescr


class NoErrorValue(ValueDescr):
    """
    A value with unspecified error
    """

    def __init__(self, ucd: str, column_name: str, units: str):
        super().__init__(ucd, column_name, units)

        self._column_name: str = column_name

    def parse_values(self, data: DataFrame) -> Series:
        return self._parse_column(data)
