import json
from dataclasses import dataclass
from typing import Any

from astropy import units as u
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

    @staticmethod
    def load(data: dict[str, Any] | None = None) -> "ObjectInfo":
        data = data or {}
        obj = ObjectInfo()

        if "names" in data:
            obj.names = data["names"]

        if "primary_name" in data:
            obj.primary_name = data["primary_name"]

        if "coordinates" in data:
            coordinates = data["coordinates"]

            if coordinates is not None:
                obj.coordinates = ICRS(ra=coordinates["ra"] * u.deg, dec=coordinates["dec"] * u.deg)

        return obj


class ObjectInfoEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, ObjectInfo):
            return json.JSONEncoder.default(self, obj)

        data = {}

        if obj.names is not None:
            data["names"] = obj.names

        if obj.primary_name is not None:
            data["primary_name"] = obj.primary_name

        if obj.coordinates is not None:
            data["coordinates"] = {
                "ra": obj.coordinates.ra.deg,
                "dec": obj.coordinates.dec.deg,
            }

        return data


@dataclass
class ObjectProcessingInfo:
    object_id: str
    status: enums.ObjectProcessingStatus
    metadata: dict[str, Any]
    data: ObjectInfo
    pgc: int | None = None
