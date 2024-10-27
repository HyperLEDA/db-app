import json
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


class ObjectInfoDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, object_hook=self.object_hook, **kwargs)

    def object_hook(self, data):
        if "coordinates" in data:
            coordinates = data["coordinates"]
            ra = coordinates.get("ra")
            dec = coordinates.get("dec")

            if ra is not None and dec is not None:
                data["coordinates"] = ICRS(ra=ra, dec=dec)

        return ObjectInfo(**data)


@dataclass
class ObjectProcessingInfo:
    object_id: str
    status: enums.ObjectProcessingStatus
    metadata: dict[str, Any]
    data: ObjectInfo
    pgc: int | None = None
