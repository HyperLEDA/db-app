from typing import Any

from app.data import model
from app.domain.responders import interface
from app.presentation import dataapi


def objects_to_response(objects: list[model.Layer2CatalogObject]) -> list[dataapi.PGCObject]:
    response_objects = []
    for obj in objects:
        catalog_data = {o.catalog().value: o.layer2_data() for o in obj.data}
        response_objects.append(dataapi.PGCObject(pgc=obj.pgc, catalogs=catalog_data))

    return response_objects


class JSONResponder(interface.ObjectResponder):
    def build_response_from_catalog(self, objects: list[model.Layer2CatalogObject]) -> Any:
        return objects_to_response(objects)
