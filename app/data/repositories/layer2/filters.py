import abc
from typing import Any, final

from astropy.units import quantity

from app.lib import astronomy


class Filter(abc.ABC):
    @abc.abstractmethod
    def get_query(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> list[Any]:
        pass


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


@final
class DesignationLikeFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "designation_like"

    def get_query(self):
        return "designation.design ILIKE CONCAT('%%', sp.params->>'design', '%%')"

    def get_params(self):
        return []


@final
class ICRSCoordinatesInRadiusFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "coordinates_in_radius"

    def __init__(self, radius: float | quantity.Quantity):
        if isinstance(radius, quantity.Quantity):
            radius = astronomy.to(radius, "deg")

        self._radius = radius

    def get_query(self):
        return """
        ST_DWithin(
            ST_MakePoint((sp.params->>'dec')::float, (params->>'ra')::float-180), 
            ST_MakePoint(layer2.icrs.dec, layer2.icrs.ra-180),
            %s
        )
        """

    def get_params(self):
        return [self._radius]


@final
class RedshiftCloseFilter(Filter):
    @classmethod
    def name(cls) -> str:
        return "redshift_close"

    def __init__(self, redshift: float, distance_percent: float):
        self._redshift = redshift
        self._distance_percent = distance_percent

    def get_query(self):
        return "abs(cz.cz - %s) / cz.cz < %s / 100"

    def get_params(self):
        return [self._redshift, self._distance_percent]
