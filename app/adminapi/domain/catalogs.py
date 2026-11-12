from typing import final

from app.adminapi import repository
from app.catalogs import layer1
from app.specs import adminapi as spec


@final
class CatalogManager:
    def __init__(self, repo: repository.Repository) -> None:
        self._repo = repo

    def get_catalogs(self) -> spec.GetCatalogsResponse:
        catalog_schemas: list[spec.CatalogSchema] = []
        for catalog in layer1.Catalog:
            object_cls = layer1.get_catalog_object_type(catalog)
            layer1_table = object_cls.layer1_table()
            schema, table = layer1_table.split(".", maxsplit=1)
            table_info = self._repo.get_table_metadata(schema, table)
            fields = [spec.field_from_column(col) for col in layer1.writable_columns(table_info)]
            catalog_schemas.append(
                spec.CatalogSchema(
                    catalog=catalog.value,
                    title=object_cls.title(),
                    description=object_cls.description(),
                    fields=fields,
                )
            )
        return spec.GetCatalogsResponse(catalogs=catalog_schemas)
