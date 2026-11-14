from typing import final

import psycopg
from astropy import units as u

from app.adminapi import repository
from app.adminapi.clients.prefect import PrefectClient
from app.catalogs import layer1
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec


@final
class Layer1Writer:
    def __init__(self, repo: repository.Repository, prefect: PrefectClient) -> None:
        self._repo = repo
        self._prefect = prefect

    def save_data(self, request: spec.SaveStructuredDataRequest) -> spec.SaveStructuredDataResponse:
        catalog = layer1.Catalog(request.catalog)
        object_cls = layer1.get_catalog_object_type(catalog)
        table = object_cls.layer1_table()

        internal_units = self._repo.get_column_units(catalog)
        missing = [col for col in request.columns if col in internal_units and col not in request.units]
        if missing:
            raise RuleValidationError(f"units required for columns: {', '.join(sorted(missing))}")

        factors: list[float | None] = [None] * len(request.columns)
        for j, col in enumerate(request.columns):
            if col in internal_units and col in request.units:
                factors[j] = (1.0 * u.Unit(request.units[col])).to(u.Unit(internal_units[col])).value
            else:
                factors[j] = None

        converted = []
        for row in request.data:
            new_row = []
            for value, factor in zip(row, factors, strict=True):
                if factor is not None:
                    new_row.append(float(value) * factor)
                else:
                    new_row.append(value)
            converted.append(new_row)

        converted = layer1.normalize_catalog_rows(catalog, request.columns, converted)

        try:
            conflict_keys = object_cls.layer1_primary_keys()
            self._repo.save_structured_data(table, request.columns, request.ids, converted, conflict_keys=conflict_keys)
        except psycopg.errors.ForeignKeyViolation as e:
            raise RuleValidationError(layer1.format_foreign_key_violation(e)) from e

        return spec.SaveStructuredDataResponse()

    def start_upload(self, request: spec.StartStructuredUploadRequest) -> spec.StartStructuredUploadResponse:
        try:
            catalog = layer1.Catalog(request.catalog)
        except ValueError as exc:
            raise NotFoundError(entity_name="catalog", entity=request.catalog) from exc

        object_cls = layer1.get_catalog_object_type(catalog)
        flow_run_id = self._prefect.create_flow_run(
            name=f"{object_cls.title()}/upload-{catalog.value}",
            parameters={"params": request.params},
        )
        return spec.StartStructuredUploadResponse(flow_run_id=flow_run_id)
