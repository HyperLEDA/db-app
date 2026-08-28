from typing import Any, final

from app.data import model, repositories
from app.specs import adminapi

_INTERNAL_COLUMNS = frozenset({"record_id", "object_id", "id"})


def _field_from_row(row: dict[str, Any]) -> adminapi.CatalogField:
    param = row.get("param") or {}
    if not isinstance(param, dict):
        param = {}
    description = param.get("description")
    return adminapi.CatalogField(
        name=row["column_name"],
        data_type=adminapi.postgres_type_to_datatype(row["data_type"]),
        unit=param.get("unit"),
        required=bool(row["not_null"]),
        ucd=param.get("ucd"),
        description=str(description) if description else "",
    )


@final
class CatalogManager:
    def __init__(self, layer1_repo: repositories.Layer1Repository) -> None:
        self._layer1_repo = layer1_repo

    def get_catalogs(self) -> adminapi.GetCatalogsResponse:
        catalogs: list[adminapi.CatalogSchema] = []
        for catalog in model.RawCatalog:
            if catalog in model.RUNTIME_RAW_CATALOGS:
                continue
            object_cls = model.get_catalog_object_type(catalog)
            layer1_table = object_cls.layer1_table()
            schema, table = layer1_table.split(".", maxsplit=1)
            rows = self._layer1_repo.get_catalog_columns(schema, table)
            fields = [_field_from_row(row) for row in rows if row["column_name"] not in _INTERNAL_COLUMNS]
            catalogs.append(
                adminapi.CatalogSchema(
                    catalog=catalog.value,
                    title=object_cls.title(),
                    description=object_cls.description(),
                    fields=fields,
                )
            )
        return adminapi.GetCatalogsResponse(catalogs=catalogs)
