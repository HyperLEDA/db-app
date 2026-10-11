import datetime
import math
from collections.abc import Sequence
from typing import Any, final

import numpy as np
import structlog
from astropy import table
from astropy import units as u
from psycopg import sql

from app.catalogs import layer1, layer2
from app.lib.storage import postgres

_DEFAULT_E_CZ = u.Quantity(100, u.Unit("km/s"))


@final
class Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def get_last_update_time(self, catalog: layer2.Catalog) -> datetime.datetime:
        return self._storage.query_one("SELECT dt FROM layer2.last_update WHERE catalog = %s", params=[catalog.value])[
            "dt"
        ]

    def update_last_update_time(self, dt: datetime.datetime, catalog: layer2.Catalog) -> None:
        self._storage.exec(
            "UPDATE layer2.last_update SET dt = %s WHERE catalog = %s",
            params=[dt, catalog.value],
        )

    def get_orphaned_pgcs(self, raw_catalogs: list[layer2.Catalog]) -> dict[str, list[int]]:
        result: dict[str, list[int]] = {}
        for catalog in raw_catalogs:
            object_cls = layer2.get_catalog_object_type(catalog)
            layer2_table = object_cls.table()
            missing_sources = []
            for source in object_cls.sources():
                layer1_table = layer1.get_catalog_object_type(source).layer1_table()
                missing_sources.append(f"""
                    NOT EXISTS (
                        SELECT 1
                        FROM layer0.records r
                        INNER JOIN {layer1_table} l1 ON l1.record_id = r.id
                        WHERE r.pgc = l2.pgc
                    )
                """)
            query = f"""
                SELECT l2.pgc FROM {layer2_table} l2
                WHERE {" AND ".join(missing_sources)}
            """
            rows_result = self._storage.query(query)
            result[layer2_table] = [int(row["pgc"]) for row in rows_result]
        return result

    def remove_pgcs(self, raw_catalogs: list[layer2.Catalog], pgcs: list[int]) -> None:
        if not pgcs:
            return

        for catalog in raw_catalogs:
            object_cls = layer2.get_catalog_object_type(catalog)
            layer2_table = object_cls.table()
            query = f"DELETE FROM {layer2_table} WHERE pgc = ANY(%s)"
            self._storage.exec(query, params=[pgcs])

    def save(self, table_name: str, data: table.QTable) -> None:
        if len(data) == 0:
            return

        schema, relation = table_name.split(".", maxsplit=1)
        table_info = self.get_table_metadata(schema, relation)
        column_units = {name: col.unit for name, col in table_info.columns.items() if col.unit}

        work = table.QTable(data, copy=True)
        columns = [name for name in work.colnames if name != "pgc"]
        for col in columns:
            target_unit = column_units.get(col)
            if target_unit is not None and work[col].unit is not None:
                work[col] = work[col].to(u.Unit(target_unit))

        all_columns = ["pgc", *columns]
        column_idents = sql.SQL(", ").join(sql.Identifier(c) for c in all_columns)
        table_ident = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(relation))
        on_conflict = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in all_columns
        )

        pgcs = [int(pgc) for pgc in work["pgc"]]
        col_values = [_column_as_list(work[col]) for col in columns]

        with self.with_tx():
            with self._storage.get_connection().cursor() as cur:
                cur.execute(
                    sql.SQL("CREATE TEMP TABLE save_staging (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(
                        table_ident
                    )
                )
                with cur.copy(sql.SQL("COPY save_staging ({}) FROM STDIN").format(column_idents)) as copy:
                    for i, pgc in enumerate(pgcs):
                        copy.write_row((pgc, *[vals[i] for vals in col_values]))
                cur.execute(
                    sql.SQL(
                        "INSERT INTO {} ({}) SELECT {} FROM save_staging ON CONFLICT (pgc) DO UPDATE SET {}"
                    ).format(table_ident, column_idents, column_idents, on_conflict)
                )

    def get_changed_pgcs(self, dt: datetime.datetime, limit: int, offset: int) -> list[int]:
        rows = self._storage.query(
            """
            SELECT id
            FROM common.pgc
            WHERE modification_time > %s AND id > %s
            ORDER BY id
            LIMIT %s
            """,
            params=[dt, offset, limit],
        )
        return [int(row["id"]) for row in rows]

    def get_summary_base_rows(self, pgcs: list[int]) -> table.QTable:
        if not pgcs:
            return table.QTable(
                {
                    "pgc": [],
                    "design": [],
                    "ra": [],
                    "e_ra": [],
                    "dec": [],
                    "e_dec": [],
                    "type_name": [],
                }
            )
        rows = self._storage.query(
            """
            SELECT p.id AS pgc, d.design, i.ra, i.e_ra, i.dec, i.e_dec, n.type_name
            FROM unnest(%s::integer[]) AS p(id)
            LEFT JOIN layer2.designation AS d ON d.pgc = p.id
            LEFT JOIN layer2.icrs AS i ON i.pgc = p.id
            LEFT JOIN layer2.nature AS n ON n.pgc = p.id
            """,
            params=[pgcs],
        )
        return table.QTable(
            {
                "pgc": [int(row["pgc"]) for row in rows],
                "design": _masked_text([row["design"] for row in rows]),
                "ra": [_optional_float(row["ra"]) for row in rows],
                "e_ra": [_optional_float(row["e_ra"]) for row in rows],
                "dec": [_optional_float(row["dec"]) for row in rows],
                "e_dec": [_optional_float(row["e_dec"]) for row in rows],
                "type_name": _masked_text([row["type_name"] for row in rows]),
            }
        )

    def get_total_photometry(
        self,
        pgcs: list[int],
        band: str,
        methods: Sequence[str],
        quality: str,
    ) -> table.QTable:
        if not pgcs:
            return table.QTable({"pgc": [], "mag": [], "e_mag": [], "datatype": []})
        rows = self._storage.query(
            """
            SELECT r.pgc, pt.mag, pt.e_mag, t.datatype
            FROM photometry.total AS pt
            JOIN layer0.records AS r ON pt.record_id = r.id
            JOIN layer0.tables AS t ON r.table_id = t.id
            WHERE r.pgc = ANY(%s)
              AND pt.band = %s
              AND pt.method::text = ANY(%s)
              AND pt.quality::text = %s
            """,
            params=[pgcs, band, list(methods), quality],
        )
        return table.QTable(
            {
                "pgc": [int(row["pgc"]) for row in rows],
                "mag": [float(row["mag"]) for row in rows],
                "e_mag": [_optional_float(row["e_mag"]) for row in rows],
                "datatype": [_enum_value(row["datatype"]) for row in rows],
            }
        )

    def get_ellipse_geometry(
        self,
        pgcs: list[int],
        band: str,
        methods: Sequence[str],
        isophote: float,
        quality: str,
    ) -> table.QTable:
        if not pgcs:
            return table.QTable({"pgc": [], "a": [], "b": [], "datatype": []})
        rows = self._storage.query(
            """
            SELECT r.pgc, e.a, e.b, t.datatype
            FROM photometry.ellipse AS e
            JOIN layer0.records AS r ON e.record_id = r.id
            JOIN layer0.tables AS t ON r.table_id = t.id
            WHERE r.pgc = ANY(%s)
              AND e.band = %s
              AND e.method::text = ANY(%s)
              AND e.isophote = %s
              AND e.quality::text = %s
            """,
            params=[pgcs, band, list(methods), isophote, quality],
        )
        return table.QTable(
            {
                "pgc": [int(row["pgc"]) for row in rows],
                "a": [_optional_float(row["a"]) for row in rows],
                "b": [_optional_float(row["b"]) for row in rows],
                "datatype": [_enum_value(row["datatype"]) for row in rows],
            }
        )

    def get_new_nature_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records("nature.data", "l1.type_name", dt, limit, offset)
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "type_name": [r["type_name"] for r in rows],
            }
        )

    def get_new_icrs_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records(
            "icrs.data",
            "l1.ra, l1.e_ra, l1.dec, l1.e_dec, t.datatype",
            dt,
            limit,
            offset,
            extra_joins="JOIN layer0.tables AS t ON o.table_id = t.id",
        )
        icrs_table = layer1.get_catalog_object_type(layer1.Catalog.ICRS).layer1_table()
        icrs_schema, icrs_name = icrs_table.split(".", maxsplit=1)
        icrs_info = self.get_table_metadata(icrs_schema, icrs_name)
        units = {name: col.unit for name, col in icrs_info.columns.items() if col.unit}
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "ra": u.Quantity([float(r["ra"]) for r in rows], u.Unit(units["ra"])),
                "e_ra": u.Quantity([float(r["e_ra"]) for r in rows], u.Unit(units["e_ra"])),
                "dec": u.Quantity([float(r["dec"]) for r in rows], u.Unit(units["dec"])),
                "e_dec": u.Quantity([float(r["e_dec"]) for r in rows], u.Unit(units["e_dec"])),
                "datatype": [r["datatype"].value for r in rows],
            }
        )

    def get_new_redshift_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records(
            "cz.data",
            "l1.cz, l1.e_cz, t.datatype",
            dt,
            limit,
            offset,
            extra_joins="JOIN layer0.tables AS t ON o.table_id = t.id",
        )
        redshift_table = layer1.get_catalog_object_type(layer1.Catalog.REDSHIFT).layer1_table()
        redshift_schema, redshift_name = redshift_table.split(".", maxsplit=1)
        redshift_info = self.get_table_metadata(redshift_schema, redshift_name)
        units = {name: col.unit for name, col in redshift_info.columns.items() if col.unit}
        e_cz_unit = u.Unit(units["e_cz"])
        default_e_cz = float(_DEFAULT_E_CZ.to_value(e_cz_unit))
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "cz": u.Quantity([float(r["cz"]) for r in rows], u.Unit(units["cz"])),
                "e_cz": u.Quantity(
                    [float(r["e_cz"]) if r["e_cz"] is not None else default_e_cz for r in rows],
                    e_cz_unit,
                ),
                "datatype": [r["datatype"].value for r in rows],
            }
        )

    def get_new_designation_records(self, dt: datetime.datetime, limit: int, offset: int) -> table.QTable:
        rows = self._query_new_pgc_records("designation.data", "l1.design", dt, limit, offset)
        return table.QTable(
            {
                "pgc": [int(r["pgc"]) for r in rows],
                "design": [r["design"] for r in rows],
            }
        )

    def get_table_metadata(self, schema: str, table: str) -> postgres.TableInfo:
        return postgres.get_table_metadata(self._storage, schema, table)

    def _query_new_pgc_records(
        self,
        layer1_table: str,
        select_columns: str,
        dt: datetime.datetime,
        limit: int,
        offset: int,
        extra_joins: str = "",
    ) -> list[dict[str, Any]]:
        query = f"""SELECT o.pgc, {select_columns}
        FROM {layer1_table} AS l1
        JOIN layer0.records AS o ON l1.record_id = o.id
        {extra_joins}
        WHERE o.pgc IN (
            SELECT DISTINCT o.pgc
            FROM {layer1_table} AS l1
            JOIN layer0.records AS o ON l1.record_id = o.id
            JOIN common.pgc AS p ON p.id = o.pgc
            WHERE p.modification_time > %s AND o.pgc > %s
            ORDER BY o.pgc
            LIMIT %s
        )
        ORDER BY o.pgc ASC"""
        return self._storage.query(query, params=[dt, offset, limit])


def _column_as_list(col: Any) -> list[Any]:
    values = col.value if getattr(col, "unit", None) is not None else col
    mask = getattr(values, "mask", None)
    if mask is None or np.ndim(mask) == 0:
        mask = getattr(col, "mask", None)
    data = np.ma.getdata(values) if np.ma.isMaskedArray(values) else np.asarray(values)
    mask_array = np.asarray(mask, dtype=bool) if mask is not None and np.ndim(mask) > 0 else None
    result: list[Any] = []
    for index, raw in enumerate(data):
        if mask_array is not None and bool(mask_array[index]):
            result.append(None)
            continue
        if raw is None or raw is np.ma.masked:
            result.append(None)
            continue
        if isinstance(raw, np.generic):
            raw = raw.item()
        if isinstance(raw, float) and math.isnan(raw):
            result.append(None)
            continue
        result.append(raw)
    return result


def _optional_float(value: Any) -> float:
    if value is None:
        return float(np.nan)
    return float(value)


def _enum_value(value: Any) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _masked_text(values: list[str | None]) -> table.MaskedColumn:
    return table.MaskedColumn(
        data=["" if value is None else value for value in values],
        mask=[value is None for value in values],
        dtype=str,
    )
