from app.data import model, repositories
from app.data.repositories import layer2
from app.presentation import dataapi

ENABLED_CATALOGS = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
]


class Actions(dataapi.Actions):
    def __init__(self, layer2_repo: repositories.Layer2Repository) -> None:
        self.layer2_repo = layer2_repo

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
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

        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            layer2.AndFilter(filters),
            layer2.CombinedSearchParams(search_params),
            query.page_size,
            query.page,
        )

        response_objects = []
        for obj in objects:
            catalog_data = {o.catalog().value: o.layer2_data() for o in obj.data}

            response_objects.append(dataapi.PGCObject(obj.pgc, catalog_data))

        return dataapi.QuerySimpleResponse(response_objects)

    def query(self, query: dataapi.QueryRequest) -> dataapi.QueryResponse:
        return dataapi.QueryResponse([])
