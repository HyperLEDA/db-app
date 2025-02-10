import abc
from typing import Any


class Filter(abc.ABC):
    @abc.abstractmethod
    def get_query(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> list[Any]:
        pass


class PGCOneOfFilter(Filter):
    def __init__(self, pgcs: list[int]):
        self._pgcs = pgcs

    def get_query(self):
        return "pgc IN ({})".format(", ".join(["%s"] * len(self._pgcs)))

    def get_params(self):
        return self._pgcs


class AndFilter(Filter):
    def __init__(self, filters: list[Filter]):
        self._filters = filters

    def get_query(self):
        return " AND ".join([f"({f.get_query()})" for f in self._filters])

    def get_params(self):
        params = []

        for f in self._filters:
            params.extend(f.get_params())

        return params


class DesignationEqualsFilter(Filter):
    def __init__(self, designation: str):
        self._designation = designation

    def get_query(self):
        return "designation.design = %s"

    def get_params(self):
        return [self._designation]


class DesignationCloseFilter(Filter):
    def __init__(self, designation: str, distance: int):
        self._designation = designation
        self._distance = distance

    def get_query(self):
        return "levenshtein_less_equal(designation.design, %s, %s) < %s"

    def get_params(self):
        return [self._designation, self._distance, self._distance]


class ICRSCoordinatesInRadiusFilter(Filter):
    def __init__(self, ra: float, dec: float, radius: float):
        self._ra = ra
        self._dec = dec
        self._radius = radius

    def get_query(self):
        return """
        ST_Distance(ST_MakePoint(%s, %s-180), ST_MakePoint(icrs.dec, icrs.ra-180)) < %s
        """

    def get_params(self):
        return [self._dec, self._ra, self._radius]


class RedshiftCloseFilter(Filter):
    def __init__(self, redshift: float, distance_percent: float):
        self._redshift = redshift
        self._distance_percent = distance_percent

    def get_query(self):
        return "abs(cz.cz - %s) / cz.cz < %s / 100"

    def get_params(self):
        return [self._redshift, self._distance_percent]
