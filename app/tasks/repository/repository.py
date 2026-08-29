import datetime
from typing import Any, final

import structlog
from astropy import table
from astropy import units as u
from psycopg import sql

from app import catalogs
from app.lib.storage import postgres

_DEFAULT_E_CZ = u.Quantity(100, u.Unit("km/s"))


@final
class Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def get_last_update_time(self, catalog: catalogs.RawCatalog) -> datetime.datetime:
        return self._storage.query_one("SELECT dt FROM layer2.last_update WHERE catalog = %s", params=[catalog.value])[
            "dt"
        ]

    def update_last_update_time(self, dt: datetime.datetime, catalog: catalogs.RawCatalog) -> None:
        self._storage.exec(
            "UPDATE layer2.last_update SET dt = %s WHERE catalog = %s",
            params=[dt, catalog.value],
        )

    def get_orphaned_pgcs(self, raw_catalogs: list[catalogs.RawCatalog]) -> dict[str, list[int]]:
        result: dict[str, list[int]] = {}
        for catalog in raw_catalogs:
            object_cls = catalogs.get_catalog_object_type(catalog)
            layer2_table = object_cls.layer2_table()
            layer1_table = object_cls.layer1_table()
            query = f"""
                SELECT l2.pgc FROM {layer2_table} l2
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM layer0.records r
                    INNER JOIN {layer1_table} l1 ON l1.record_id = r.id
                    WHERE r.pgc = l2.pgc
                )
            """
            rows_result = self._storage.query(query)
            result[layer2_table] = [int(row["pgc"]) for row in rows_result]
        return result

    def remove_pgcs(self, raw_catalogs: list[catalogs.RawCatalog], pgcs: list[int]) -> None:
        if not pgcs:
            return

        for catalog in raw_catalogs:
            object_cls = catalogs.get_catalog_object_type(catalog)
            layer2_table = object_cls.layer2_table()
            query = f"DELETE FROM {layer2_table} WHERE pgc = ANY(%s)"
            self._storage.exec(query, params=[pgcs])

    def save(self, table_name: str, data: table.QTable) -> None:
        if len(data) == 0:
            return

        schema, relation = table_name.split(".", maxsplit=1)
        column_units = self._get_column_units(schema, relation)

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
        units = self._get_layer1_column_units(catalogs.RawCatalog.ICRS)
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
        units = self._get_layer1_column_units(catalogs.RawCatalog.REDSHIFT)
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

    def _get_column_units(self, schema: str, table_name: str) -> dict[str, str]:
        rows = self._storage.query(
            "SELECT column_name, param->>'unit' as unit FROM meta.column_info "
            "WHERE schema_name = %s AND table_name = %s AND param->>'unit' IS NOT NULL",
            params=[schema, table_name],
        )
        return {row["column_name"]: row["unit"] for row in rows}

    def _get_layer1_column_units(self, catalog: catalogs.RawCatalog) -> dict[str, str]:
        object_cls = catalogs.get_catalog_object_type(catalog)
        schema, table_name = object_cls.layer1_table().split(".")
        return self._get_column_units(schema, table_name)

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
    if getattr(col, "unit", None) is not None:
        return col.value.tolist()
    return [v.item() if hasattr(v, "item") else v for v in col]
