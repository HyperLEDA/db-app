from typing import Any, final

from app.adminapi import repository
from app.data import model
from app.specs import adminapi as spec

_INTERNAL_COLUMNS = frozenset({"record_id", "object_id", "id"})


def _field_from_row(row: dict[str, Any]) -> spec.CatalogField:
    param = row.get("param") or {}
    if not isinstance(param, dict):
        param = {}
    description = param.get("description")
    return spec.CatalogField(
        name=row["column_name"],
        data_type=spec.postgres_type_to_datatype(row["data_type"]),
        unit=param.get("unit"),
        required=bool(row["not_null"]),
        ucd=param.get("ucd"),
        description=str(description) if description else "",
    )


@final
class CatalogManager:
    def __init__(self, repo: repository.Repository) -> None:
        self._repo = repo

    def get_catalogs(self) -> spec.GetCatalogsResponse:
        catalogs: list[spec.CatalogSchema] = []
        for catalog in model.RawCatalog:
            if catalog in model.RUNTIME_RAW_CATALOGS:
                continue
            object_cls = model.get_catalog_object_type(catalog)
            layer1_table = object_cls.layer1_table()
            schema, table = layer1_table.split(".", maxsplit=1)
            rows = self._repo.get_catalog_columns(schema, table)
            fields = [_field_from_row(row) for row in rows if row["column_name"] not in _INTERNAL_COLUMNS]
            catalogs.append(
                spec.CatalogSchema(
                    catalog=catalog.value,
                    title=object_cls.title(),
                    description=object_cls.description(),
                    fields=fields,
                )
            )
        return spec.GetCatalogsResponse(catalogs=catalogs)
