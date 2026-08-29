import abc
import math
from typing import Any, final, override

from astropy import units as u

from app.lib import astronomy

# Because postgis is a geography extension we have to do some trickery to convert degrees on the celestial sphere
# efficiently to Earth's coordinates. This is just Earth's radius.
_SPHERE_RADIUS_M = 6371008.7714


class Filter(abc.ABC):
    @abc.abstractmethod
    def get_query(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> list[Any]:
        pass

    def driving_table(self) -> str:
        raise NotImplementedError(type(self).__name__)


@final
class PGCOneOfFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "pgc_one_of"

    def __init__(self, pgcs: list[int]):
        self._pgcs = pgcs

    def get_query(self):
        return "pgc IN ({})".format(", ".join(["%s"] * len(self._pgcs)))

    def get_params(self):
        return self._pgcs


@final
class AndFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "and"

    def __init__(self, filters: list[Filter]):
        self._filters = filters

    def get_query(self):
        return " AND ".join([f"({f.get_query()})" for f in self._filters]) or "1=1"

    def get_params(self):
        params = []

        for f in self._filters:
            params.extend(f.get_params())

        return params

    # Every conjunct must hold, so any strict child can drive the join.
    def driving_table(self) -> str:
        for f in self._filters:
            try:
                return f.driving_table()
            except NotImplementedError:
                continue

        raise NotImplementedError(type(self).__name__)


@final
class DesignationLikeFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "designation_like"

    @override
    def get_query(self):
        return "layer2.designations.design ILIKE CONCAT('%%', sp.params->>'design', '%%')"

    @override
    def get_params(self):
        return []

    @override
    def driving_table(self) -> str:
        return "layer2.designations"


@final
class ICRSCoordinatesInRadiusFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "coordinates_in_radius"

    def __init__(self, radius: u.Quantity):
        self._radius_m = math.radians(astronomy.to(radius, "deg")) * _SPHERE_RADIUS_M

    @override
    def get_query(self):
        return """
        ST_DWithin(
            ST_MakePoint((sp.params->>'ra')::float, (sp.params->>'dec')::float)::geography,
            ST_MakePoint(layer2.icrs.ra, layer2.icrs.dec)::geography,
            %s,
            false
        )
        """

    def get_params(self):
        return [self._radius_m]

    @override
    def driving_table(self) -> str:
        return "layer2.icrs"


class Ordering(abc.ABC):
    @abc.abstractmethod
    def get_query(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> list[Any]:
        pass


@final
class ICRSDistanceOrdering(Ordering):
    def __init__(self, ra: u.Quantity, dec: u.Quantity) -> None:
        self._ra = astronomy.to(ra, "deg")
        self._dec = astronomy.to(dec, "deg")

    @override
    def get_query(self) -> str:
        return """ST_Distance(
            ST_MakePoint(%s, %s)::geography,
            ST_MakePoint(layer2.icrs.ra, layer2.icrs.dec)::geography,
            false
        ), pgc"""

    def get_params(self) -> list[Any]:
        return [self._ra, self._dec]
