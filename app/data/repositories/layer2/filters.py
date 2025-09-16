import abc
from typing import Any, final

from astropy import units as u
from astropy.units import quantity

from app.data import model
from app.data.repositories.layer2 import params
from app.lib import astronomy


class Filter(abc.ABC):
    @abc.abstractmethod
    def get_query(self) -> str:
        pass

    @abc.abstractmethod
    def get_params(self) -> list[Any]:
        pass

    @abc.abstractmethod
    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
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

    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
        return params.CombinedSearchParams([])


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

    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
        search_params_list = [f.extract_search_params(object_info) for f in self._filters]
        return params.CombinedSearchParams(search_params_list)


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

    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
        search_params_list = [f.extract_search_params(object_info) for f in self._filters]
        return params.CombinedSearchParams(search_params_list)


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

    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
        return params.CombinedSearchParams([])


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

    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
        if (cat := model.get_object(object_info, model.DesignationCatalogObject)) is not None:
            return params.DesignationSearchParams(designation=cat.designation)

        return params.CombinedSearchParams([])


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

    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
        if (cat := model.get_object(object_info, model.ICRSCatalogObject)) is not None:
            return params.ICRSSearchParams(ra=cat.ra, dec=cat.dec)

        return params.CombinedSearchParams([])


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

    def extract_search_params(self, object_info: list[model.CatalogObject]) -> params.SearchParams:
        return params.CombinedSearchParams([])


AVAILABLE_FILTERS = {
    PGCOneOfFilter.name(): PGCOneOfFilter,
    AndFilter.name(): AndFilter,
    OrFilter.name(): OrFilter,
    DesignationEqualsFilter.name(): DesignationEqualsFilter,
    DesignationCloseFilter.name(): DesignationCloseFilter,
    ICRSCoordinatesInRadiusFilter.name(): ICRSCoordinatesInRadiusFilter,
    RedshiftCloseFilter.name(): RedshiftCloseFilter,
}
