from dataclasses import dataclass
from typing import Any

from astropy.coordinates import ICRS

from app.lib.storage import enums


@dataclass
class ObjectInfo:
    """
    :param names: All names, provided by source
    :param primary_name: The name, that is provided as primary by author of transaction
    :param coordinates: Sky coordinates of the object
    """

    names: list[str] | None = None
    primary_name: str | None = None
    coordinates: ICRS | None = None


@dataclass
class ObjectProcessingInfo:
    object_id: str
    status: enums.ObjectProcessingStatus
    metadata: dict[str, Any]
    pgc: int | None = None
