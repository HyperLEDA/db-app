from dataclasses import dataclass

from astropy.coordinates import ICRS


@dataclass
class CrossIdentificationParam:
    """
    :param names: All names, provided by source
    :param primary_name: The name, that is provided as primary by author of transaction
    :param coordinates: Sky coordinates of the object
    """

    names: list[str] | None
    primary_name: str | None
    coordinates: ICRS | None
