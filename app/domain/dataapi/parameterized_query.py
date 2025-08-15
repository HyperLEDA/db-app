from app.data import model, repositories
from app.data.repositories import layer2
from app.domain import responders
from app.presentation import dataapi


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
            filters.append(layer2.DesignationCloseFilter(3))
            search_params.append(layer2.DesignationSearchParams(query.name))

        if (query.cz is not None) and (query.cz_err_percent is not None):
            filters.append(layer2.RedshiftCloseFilter(query.cz, query.cz_err_percent))

        return layer2.AndFilter(filters), layer2.CombinedSearchParams(search_params)

    def query_fits(self, query: dataapi.FITSRequest) -> bytes:
        filters, search_params = self._build_filters_and_params(query)

        objects = self.layer2_repo.query(
            self.enabled_catalogs,
            filters,
            search_params,
            query.page_size,
            query.page,
        )

        responder = responders.FITSResponder()
        return responder.build_response(objects)

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        filters, search_params = self._build_filters_and_params(query)

        if not query.pgcs:
            objects = self.layer2_repo.query(
                self.enabled_catalogs,
                filters,
                search_params,
                query.page_size,
                query.page,
            )
        else:
            objects = self.layer2_repo.query_pgc(
                self.enabled_catalogs,
                query.pgcs,
                query.page_size,
                query.page,
            )

        responder = responders.StructuredResponder(self.catalog_config)
        return responder.build_response(objects)
