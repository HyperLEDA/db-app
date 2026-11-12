from typing import Any

import structlog
from astropy import units as u

from app.adminapi import model
from app.adminapi.repository.common import get_column_units as query_column_units
from app.catalogs import layer1
from app.lib.storage import postgres

log: structlog.stdlib.BoundLogger = structlog.get_logger()

DEFAULT_E_CZ = u.Quantity(100, u.Unit("km/s"))


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        log.error("Failed to parse catalog number", exc_info=exc)
        return None


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def get_column_units(self, catalog: layer1.Catalog) -> dict[str, str]:
        object_cls = layer1.get_catalog_object_type(catalog)
        schema, table_name = object_cls.layer1_table().split(".")
        return query_column_units(self._storage, schema, table_name)

    def save_structured_data(
        self,
        table: str,
        columns: list[str],
        ids: list[str],
        data: list[list[Any]],
        conflict_keys: list[str] | None = None,
    ) -> None:
        with self.with_tx():
            layer1.save_structured_data(self._storage, table, columns, ids, data, conflict_keys)

    def get_designation_records(self, record_ids: list[str]) -> list[model.DesignationRecord | None]:
        if not record_ids:
            return []
        rows = self._storage.query(
            "SELECT record_id, design FROM designation.data WHERE record_id = ANY(%s)",
            params=[record_ids],
        )
        by_id = {r["record_id"]: model.DesignationRecord(design=r["design"]) for r in rows}
        return [by_id.get(rid) for rid in record_ids]

    def get_icrs_records(self, record_ids: list[str]) -> list[model.ICRSRecord | None]:
        if not record_ids:
            return []
        rows = self._storage.query(
            "SELECT record_id, ra, e_ra, dec, e_dec FROM icrs.data WHERE record_id = ANY(%s)",
            params=[record_ids],
        )
        by_id: dict[str, model.ICRSRecord] = {}
        for row in rows:
            ra = _as_float(row["ra"])
            e_ra = _as_float(row["e_ra"])
            dec = _as_float(row["dec"])
            e_dec = _as_float(row["e_dec"])
            if ra is None or e_ra is None or dec is None or e_dec is None:
                continue
            by_id[row["record_id"]] = model.ICRSRecord(ra=ra, e_ra=e_ra, dec=dec, e_dec=e_dec)
        return [by_id.get(rid) for rid in record_ids]

    def get_redshift_records(self, record_ids: list[str]) -> list[model.RedshiftRecord | None]:
        if not record_ids:
            return []
        rows = self._storage.query(
            "SELECT record_id, cz, e_cz FROM cz.data WHERE record_id = ANY(%s)",
            params=[record_ids],
        )
        units = self.get_column_units(layer1.Catalog.REDSHIFT)
        default_e_cz = float(DEFAULT_E_CZ.to_value(u.Unit(units["e_cz"])))
        by_id: dict[str, model.RedshiftRecord] = {}
        for row in rows:
            cz = _as_float(row["cz"])
            if cz is None:
                continue
            e_cz = default_e_cz if row["e_cz"] is None else _as_float(row["e_cz"])
            if e_cz is None:
                continue
            by_id[row["record_id"]] = model.RedshiftRecord(cz=cz, e_cz=e_cz)
        return [by_id.get(rid) for rid in record_ids]

    def get_nature_records(self, record_ids: list[str]) -> list[model.NatureRecord | None]:
        if not record_ids:
            return []
        rows = self._storage.query(
            "SELECT record_id, type_name FROM nature.data WHERE record_id = ANY(%s)",
            params=[record_ids],
        )
        by_id = {r["record_id"]: model.NatureRecord(type_name=r["type_name"]) for r in rows}
        return [by_id.get(rid) for rid in record_ids]
