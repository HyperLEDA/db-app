import abc

from numpy.typing import ArrayLike


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
    def convert(self, columns: list[ArrayLike]) -> ArrayLike:
        """
        Converts list of arrays of physical quantities into commonly used form.
        """
        ...
