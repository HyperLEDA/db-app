from app.data import model, repositories
from app.data.repositories import layer2
from app.domain import responders
from app.presentation import dataapi

CATALOGS_FOR_PGC_QUERY = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ADDITIONAL_DESIGNATIONS,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
    model.RawCatalog.NATURE,
    model.RawCatalog.NOTE,
    model.RawCatalog.PHOTOMETRY__TOTAL,
]


def resolve_query_catalogs(
    catalog_names: list[str] | None,
    default_catalogs: list[model.RawCatalog],
) -> list[model.RawCatalog]:
    if catalog_names is None:
        return default_catalogs
    if not catalog_names:
        raise ValueError("catalogs must not be empty")

    allowed = set(default_catalogs)
    result: list[model.RawCatalog] = []
    seen: set[model.RawCatalog] = set()
    for name in catalog_names:
        try:
            catalog = model.RawCatalog(name)
        except ValueError as exc:
            valid = ", ".join(c.value for c in model.RawCatalog)
            raise ValueError(f"Unknown catalog {name!r}; valid values are: {valid}") from exc
        if catalog not in allowed:
            allowed_names = ", ".join(c.value for c in default_catalogs)
            raise ValueError(f"Catalog {name!r} is not available for this query; available: {allowed_names}")
        if catalog not in seen:
            seen.add(catalog)
            result.append(catalog)
    return result


class ParameterizedQueryManager:
    def __init__(
        self,
        layer2_repo: repositories.Layer2Repository,
        enabled_catalogs: list[model.RawCatalog],
        catalog_cfg: responders.CatalogConfig,
    ) -> None:
        self.layer2_repo = layer2_repo
        self.enabled_catalogs = enabled_catalogs
        self.catalog_config = catalog_cfg

    def _build_filters_and_params(
        self, query: dataapi.QuerySimpleRequest | dataapi.FITSRequest
    ) -> tuple[layer2.Filter, layer2.SearchParams]:
        filters = []
        search_params = []

        if query.pgcs is not None:
            filters.append(layer2.PGCOneOfFilter(query.pgcs))

        if (query.ra is not None) and (query.dec is not None) and (query.radius is not None):
            filters.append(layer2.ICRSCoordinatesInRadiusFilter(query.radius))
            search_params.append(layer2.ICRSSearchParams(query.ra, query.dec))

        if query.name is not None:
            filters.append(layer2.DesignationLikeFilter())
            search_params.append(layer2.DesignationSearchParams(query.name))

        if (query.cz is not None) and (query.cz_err_percent is not None):
            filters.append(layer2.RedshiftCloseFilter(query.cz, query.cz_err_percent))

        return layer2.AndFilter(filters), layer2.CombinedSearchParams(search_params)

    def query_fits(self, query: dataapi.FITSRequest) -> bytes:
        filters, search_params = self._build_filters_and_params(query)

        objects = self.layer2_repo.query_catalogs(
            self.enabled_catalogs,
            filters,
            search_params,
            query.page_size,
            query.page,
        )

        responder = responders.FITSResponder()
        return responder.build_response_from_catalog(objects)

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        responder = responders.StructuredResponder(self.catalog_config)
        if query.pgcs:
            catalogs = resolve_query_catalogs(query.catalogs, CATALOGS_FOR_PGC_QUERY)
            objects = self.layer2_repo.query_pgc(
                catalogs,
                query.pgcs,
                query.page_size,
                query.page,
            )
            return responder.build_response(objects)

        catalogs = resolve_query_catalogs(query.catalogs, self.enabled_catalogs)
        filters, search_params = self._build_filters_and_params(query)

        objects = self.layer2_repo.query_catalogs(
            catalogs,
            filters,
            search_params,
            query.page_size,
            query.page,
        )
        return responder.build_response_from_catalog(objects)
