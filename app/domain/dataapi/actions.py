from app.data import model, repositories
from app.data.repositories import layer2_repository
from app.lib import containers
from app.presentation import dataapi

ENABLED_CATALOGS = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
]


class Actions(dataapi.Actions):
    def __init__(self, layer2_repo: repositories.Layer2Repository) -> None:
        self.layer2_repo = layer2_repo

    def query_simple(self, query: dataapi.QuerySimpleRequest) -> dataapi.QuerySimpleResponse:
        filters = []

        if (query.ra is not None) and (query.dec is not None) and (query.radius is not None):
            filters.append(layer2_repository.ICRSCoordinatesInRadiusFilter(query.ra, query.dec, query.radius))

        if query.name is not None:
            filters.append(layer2_repository.DesignationEqualsFilter(query.name))

        objects = self.layer2_repo.query(ENABLED_CATALOGS, filters, query.page_size, query.page)

        objects_by_pgc = containers.group_by(objects, key_func=lambda obj: obj.pgc())

        response_objects = []
        for pgc, catalogs in objects_by_pgc.items():
            catalog_data = {obj.catalog().value: obj.layer2_data() for obj in catalogs}

            response_objects.append(dataapi.PGCObject(pgc, catalog_data))

        return dataapi.QuerySimpleResponse(response_objects)
