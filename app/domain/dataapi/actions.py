from typing import final

from app.data import model, repositories
from app.domain import responders
from app.domain.dataapi import parameterized_query, search_parsers
from app.presentation import dataapi

ENABLED_CATALOGS = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
    model.RawCatalog.NATURE,
]


@final
class Actions(dataapi.Actions):
    def __init__(
        self,
        layer2_repo: repositories.Layer2Repository,
        catalog_cfg: responders.CatalogConfig,
    ) -> None:
        self.layer2_repo = layer2_repo
        self.catalog_cfg = catalog_cfg
        self.parameterized_query_manager = parameterized_query.ParameterizedQueryManager(
            layer2_repo, ENABLED_CATALOGS, catalog_cfg
        )

    def query(self, query: dataapi.QueryRequest) -> dataapi.QueryResponse:
        filters, search_params = search_parsers.query_to_filters(query.q, search_parsers.DEFAULT_PARSERS)
        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            filters,
            search_params,
            query.page_size,
            query.page,
        )
        responder = responders.StructuredResponder(self.catalog_cfg)
        pgc_objects = responder.build_response(objects).objects
        return dataapi.QueryResponse(objects=pgc_objects)

    def query_fits(self, query: dataapi.FITSRequest) -> bytes:
        return self.parameterized_query_manager.query_fits(query)

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        return self.parameterized_query_manager.query_simple(query)
