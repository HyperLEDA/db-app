from astropy import coordinates as coords

from app import catalogs
from app.dataapi import repository, responders
from app.dataapi.domain import reddening
from app.lib import astronomy
from app.lib.web.errors import RuleValidationError
from app.specs import dataapi as spec

CATALOGS_FOR_PGC_QUERY = [
    catalogs.RawCatalog.DESIGNATION,
    catalogs.RawCatalog.ADDITIONAL_DESIGNATIONS,
    catalogs.RawCatalog.ICRS,
    catalogs.RawCatalog.REDSHIFT,
    catalogs.RawCatalog.NATURE,
    catalogs.RawCatalog.NOTE,
    catalogs.RawCatalog.PHOTOMETRY__TOTAL,
]


def resolve_query_catalogs(
    catalog_names: list[str] | None,
    default_catalogs: list[catalogs.RawCatalog],
) -> list[catalogs.RawCatalog]:
    if catalog_names is None:
        return default_catalogs
    if not catalog_names:
        raise RuleValidationError("catalogs must not be empty")

    allowed = set(default_catalogs)
    result: list[catalogs.RawCatalog] = []
    seen: set[catalogs.RawCatalog] = set()
    for name in catalog_names:
        try:
            catalog = catalogs.RawCatalog(name)
        except ValueError as exc:
            valid = ", ".join(c.value for c in catalogs.RawCatalog)
            raise RuleValidationError(f"Unknown catalog {name!r}; valid values are: {valid}") from exc
        if catalog not in allowed:
            allowed_names = ", ".join(c.value for c in default_catalogs)
            raise RuleValidationError(f"Catalog {name!r} is not available for this query; available: {allowed_names}")
        if catalog not in seen:
            seen.add(catalog)
            result.append(catalog)
    return result


def _build_filters_and_params(
    query: spec.QuerySimpleRequest,
) -> tuple[repository.Filter, repository.SearchParams, repository.Ordering | None]:
    filters = []
    search_params = []
    ordering: repository.Ordering | None = None

    if query.pgcs is not None:
        filters.append(repository.PGCOneOfFilter(query.pgcs))

    if query.radius is not None:
        icrs: coords.SkyCoord | None = None
        if query.ra is not None and query.dec is not None:
            equinox = astronomy.parse_coordinate_epoch(query.eq_epoch)
            coord = coords.SkyCoord(ra=query.ra, dec=query.dec, frame=coords.FK5(equinox=equinox))
            icrs = coord.transform_to("icrs")
        elif query.glon is not None and query.glat is not None:
            icrs = coords.SkyCoord(l=query.glon, b=query.glat, frame="galactic").transform_to("icrs")
        elif query.sgl is not None and query.sgb is not None:
            icrs = coords.SkyCoord(sgl=query.sgl, sgb=query.sgb, frame="supergalactic").transform_to("icrs")

        if icrs is not None:
            filters.append(repository.ICRSCoordinatesInRadiusFilter(query.radius))
            search_params.append(repository.ICRSSearchParams(icrs.ra, icrs.dec))
            ordering = repository.ICRSDistanceOrdering(icrs.ra, icrs.dec)

    if query.name is not None:
        filters.append(repository.DesignationLikeFilter())
        search_params.append(repository.DesignationSearchParams(query.name))

    return repository.AndFilter(filters), repository.CombinedSearchParams(search_params), ordering


class ParameterizedQueryManager:
    def __init__(
        self,
        repo: repository.Repository,
        enabled_catalogs: list[catalogs.RawCatalog],
        catalog_cfg: responders.CatalogConfig,
        reddening_service: reddening.Reddening,
    ) -> None:
        self.repo = repo
        self.enabled_catalogs = enabled_catalogs
        self.catalog_config = catalog_cfg
        self.reddening_service = reddening_service

    def query_simple(self, query: spec.QuerySimpleRequest) -> spec.QuerySimpleResponse:
        responder = responders.StructuredResponder(self.catalog_config, self.reddening_service)
        offset = query.page * query.page_size
        if query.pgcs:
            raw_catalogs = resolve_query_catalogs(query.catalogs, CATALOGS_FOR_PGC_QUERY)
            objects = self.repo.query_pgc(
                raw_catalogs,
                query.pgcs,
                query.page_size,
                offset,
            )
            return responder.build_response(objects)

        raw_catalogs = resolve_query_catalogs(query.catalogs, self.enabled_catalogs)
        filters, search_params, ordering = _build_filters_and_params(query)

        objects = self.repo.query_catalogs(
            raw_catalogs,
            filters,
            search_params,
            query.page_size,
            offset,
            ordering=ordering,
        )
        return responder.build_response_from_catalog(objects)
