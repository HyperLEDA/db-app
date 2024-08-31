import abc

import pandas
from numpy.typing import ArrayLike

from app import entities


class QuantityConverter(abc.ABC):
    """
    Base class for physical quantity conversions.
    The intended usage is to validate and convert user-provided arrays of physical quantities into some common form.

    Examples of implemetations might include but are not limited to:
    - Convert right ascension from J1950 to J2000 system.
    - Combine 3 columns `ra_h`, `ra_m`, `ra_s` into a single valid array of right ascension objects.
    - Convert error of the physical quantity into the same form as the base quantity.
    """

    @abc.abstractmethod
    def parse_columns(self, columns: list[entities.ColumnDescription]) -> None:
        """
        Adds columns' metadata to the definition of the converter.
        If a column does not belong to the converter, it should be ignored.
        If a column does belong to the converter but introduces ambiguity, `ConverterError` should be raised.
        """
        ...

    @abc.abstractmethod
    def convert(self, data: pandas.DataFrame) -> ArrayLike:
        """
        Converts DataFrame of data into common form of this physical quantity.
        """
        ...
