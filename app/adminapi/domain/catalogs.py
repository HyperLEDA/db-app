from typing import Any, final

from app.adminapi import presentation as adminapi
from app.data import model, repositories

_INTERNAL_COLUMNS = frozenset({"record_id", "object_id", "id", "modification_time"})

_CATALOG_DISPLAY: dict[model.RawCatalog, tuple[str, str]] = {
    model.RawCatalog.ICRS: ("ICRS", "Equatorial coordinates in the ICRS frame."),
    model.RawCatalog.DESIGNATION: ("Designations", "Object designations."),
    model.RawCatalog.REDSHIFT: ("Redshift", "Heliocentric velocity (cz)."),
    model.RawCatalog.NATURE: ("Nature", "Object type classification."),
    model.RawCatalog.PHOTOMETRY__TOTAL: ("Photometry (total)", "Total magnitudes per band and method."),
    model.RawCatalog.PHOTOMETRY__ISOPHOTAL: ("Photometry (isophotal)", "Isophotal magnitudes per band and level."),
    model.RawCatalog.GEOMETRY: ("Geometry", "Isophotal ellipse geometry."),
    model.RawCatalog.NOTE: ("Note", "Free-text notes attached to records."),
}


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
            title, description = _CATALOG_DISPLAY.get(catalog, (catalog.value, ""))
            catalogs.append(
                adminapi.CatalogSchema(
                    catalog=catalog.value,
                    title=title,
                    description=description,
                    fields=fields,
                )
            )
        return adminapi.GetCatalogsResponse(catalogs=catalogs)
