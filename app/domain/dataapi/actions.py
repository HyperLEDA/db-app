from app.data import model, repositories
from app.data.repositories import layer2_repository
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

        if query.pgcs is not None:
            filters.append(layer2_repository.PGCOneOfFilter(query.pgcs))

        if (query.ra is not None) and (query.dec is not None) and (query.radius is not None):
            filters.append(layer2_repository.ICRSCoordinatesInRadiusFilter(query.ra, query.dec, query.radius))

        if query.name is not None:
            filters.append(layer2_repository.DesignationCloseFilter(query.name, 3))

        if (query.cz is not None) and (query.cz_err_percent is not None):
            filters.append(layer2_repository.RedshiftCloseFilter(query.cz, query.cz_err_percent))

        objects = self.layer2_repo.query(
            ENABLED_CATALOGS,
            layer2_repository.AndFilter(filters),
            query.page_size,
            query.page,
        )

        response_objects = []
        for obj in objects:
            catalog_data = {o.catalog().value: o.layer2_data() for o in obj.data}

            response_objects.append(dataapi.PGCObject(obj.pgc, catalog_data))

        return dataapi.QuerySimpleResponse(response_objects)
