import abc

import pandas
from numpy.typing import ArrayLike

from app import entities


class QuantityConverter(abc.ABC):
    """
    Base class for conversions of physical quantities.
    The intended use is to validate and convert user supplied arrays of physical quantities into a common form.

    Examples of implementations could include, but are not limited to
    - Convert right ascension from a J1950 system to a J2000 system.
    - Combine 3 columns `ra_h`, `ra_m`, `ra_s` into a single valid array of right ascension objects.
    - Convert the error of the physical quantity into the same form as the base quantity.
    - Convert the name of the object into a common form without abbreviations.
    """

    @abc.abstractmethod
    def name(self) -> str:
        """
        Returns the identification name of the converter.
        It is usually used in errors or in other feedback for the user.
        """
        ...

    @abc.abstractmethod
    def parse_columns(self, columns: list[entities.ColumnDescription]) -> None:
        """
        Adds columns' metadata to the definition of the converter.

        - If a column does not belong to the converter, it is ignored.
        - If a column does belong to the converter but introduces ambiguity, `ConverterError` is raised.
        - If all of the supplied columns do not contain enough information to uniquely convert any given data,
        `ConverterNoColumnError` is raised.
        """
        ...

    @abc.abstractmethod
    def convert(self, data: pandas.DataFrame) -> ArrayLike:
        """
        Converts DataFrame of data into common form of this physical quantity.
        """
        ...
