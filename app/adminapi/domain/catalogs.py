from typing import final

from app import catalogs
from app.adminapi import repository
from app.lib.storage import postgres
from app.specs import adminapi as spec

_INTERNAL_COLUMNS = frozenset({"record_id", "object_id", "id"})


def _field_from_column(col: postgres.ColumnInfo) -> spec.CatalogField:
    return spec.CatalogField(
        name=col.name,
        data_type=spec.postgres_type_to_datatype(col.data_type),
        unit=col.unit,
        required=col.not_null,
        ucd=col.ucd,
        description=str(col.description) if col.description else "",
    )


@final
class CatalogManager:
    def __init__(self, repo: repository.Repository) -> None:
        self._repo = repo

    def get_catalogs(self) -> spec.GetCatalogsResponse:
        catalog_schemas: list[spec.CatalogSchema] = []
        for catalog in catalogs.RawCatalog:
            if catalog in catalogs.RUNTIME_RAW_CATALOGS:
                continue
            object_cls = catalogs.get_catalog_object_type(catalog)
            layer1_table = object_cls.layer1_table()
            schema, table = layer1_table.split(".", maxsplit=1)
            table_info = self._repo.get_table_metadata(schema, table)
            fields = sorted(
                [_field_from_column(col) for name, col in table_info.columns.items() if name not in _INTERNAL_COLUMNS],
                key=lambda field: field.name,
            )
            catalog_schemas.append(
                spec.CatalogSchema(
                    catalog=catalog.value,
                    title=object_cls.title(),
                    description=object_cls.description(),
                    fields=fields,
                )
            )
        return spec.GetCatalogsResponse(catalogs=catalog_schemas)
