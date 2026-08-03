import abc
import math
from typing import Any, final

from astropy import units as u

from app.lib import astronomy

# Because postgis is a geography extension we have to do some trickery to convert degrees on the celestial sphere 
# efficiently to Earth's coordinates. This is just an Earth's radius.
_SPHERE_RADIUS_M = 6371008.7714


class Filter(abc.ABC):
    @abc.abstractmethod
    def get_query(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> list[Any]:
        pass

    # Table this filter is strict on: an object missing from it can never match. Such a table can
    # drive the join, letting the rest be LEFT JOINed onto it instead of combined with FULL JOIN.
    # None means the filter can match objects missing from any single table, so FULL JOIN must stay.
    def driving_table(self) -> str | None:
        return None


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
    def driving_table(self) -> str | None:
        for f in self._filters:
            table = f.driving_table()
            if table is not None:
                return table

        return None


@final
class OrFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "or"

    def __init__(self, filters: list[Filter]):
        self._filters = filters

    def get_query(self):
        return " OR ".join([f"({f.get_query()})" for f in self._filters]) or "1=1"

    def get_params(self):
        params = []
        for f in self._filters:
            params.extend(f.get_params())
        return params

    # Only one branch has to hold, so a table may drive the join only if every branch requires it.
    def driving_table(self) -> str | None:
        tables = {f.driving_table() for f in self._filters}
        if len(tables) == 1:
            return tables.pop()

        return None


@final
class DesignationEqualsFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "designation_equals"

    def __init__(self, designation: str):
        self._designation = designation

    def get_query(self):
        return "designation.design = %s"

    def get_params(self):
        return [self._designation]

    def driving_table(self) -> str | None:
        return "layer2.designation"


@final
class DesignationCloseFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "designation_close"

    def __init__(self, distance: int):
        self._distance = distance

    def get_query(self):
        return "levenshtein_less_equal(layer2.designation.design, sp.params->>'design', %s) < %s"

    def get_params(self):
        return [self._distance, self._distance]

    def driving_table(self) -> str | None:
        return "layer2.designation"


@final
class DesignationLikeFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "designation_like"

    def get_query(self):
        return "designation.design ILIKE CONCAT('%%', sp.params->>'design', '%%')"

    def get_params(self):
        return []

    def driving_table(self) -> str | None:
        return "layer2.designation"


@final
class ICRSCoordinatesInRadiusFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "coordinates_in_radius"

    def __init__(self, radius: u.Quantity):
        self._radius_m = math.radians(astronomy.to(radius, "deg")) * _SPHERE_RADIUS_M

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

    def driving_table(self) -> str | None:
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

    def get_query(self) -> str:
        return """ST_Distance(
            ST_MakePoint(%s, %s)::geography,
            ST_MakePoint(layer2.icrs.ra, layer2.icrs.dec)::geography,
            false
        ), pgc"""

    def get_params(self) -> list[Any]:
        return [self._ra, self._dec]
