from typing import Any

import structlog
from astropy import units as u
from psycopg import sql

from app.data import model
from app.data.repositories.common import get_column_units as query_column_units
from app.data.repositories.common import touch_pgcs
from app.lib.storage import postgres

DEFAULT_E_CZ = u.Quantity(100, u.Unit("km/s"))


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def get_column_units(self, catalog: model.RawCatalog) -> dict[str, str]:
        object_cls = model.get_catalog_object_type(catalog)
        schema, table_name = object_cls.layer1_table().split(".")
        return query_column_units(self._storage, schema, table_name)

    def get_catalog_columns(self, schema: str, table: str) -> list[dict[str, Any]]:
        return self._storage.query(
            """
            SELECT c.column_name,
                   c.data_type::text AS data_type,
                   (c.is_nullable = 'NO') AS not_null,
                   ci.param
            FROM information_schema.columns c
            LEFT JOIN meta.column_info ci
              ON ci.schema_name = c.table_schema
             AND ci.table_name = c.table_name
             AND ci.column_name = c.column_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            params=[schema, table],
        )

    def save_structured_data(
        self,
        table: str,
        columns: list[str],
        ids: list[str],
        data: list[list[Any]],
        conflict_keys: list[str] | None = None,
    ) -> None:
        if conflict_keys is None:
            conflict_keys = ["record_id"]
        all_columns = ["record_id"] + columns
        schema, relation = table.split(".", maxsplit=1)
        table_ident = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(relation))
        column_idents = sql.SQL(", ").join(sql.Identifier(c) for c in all_columns)
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in all_columns)
        conflict_idents = sql.SQL(", ").join(sql.Identifier(c) for c in conflict_keys)
        update_columns = [c for c in all_columns if c not in conflict_keys]
        if update_columns:
            on_conflict_set = sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in update_columns
            )
            conflict_action = sql.SQL("ON CONFLICT ({}) DO UPDATE SET {}").format(conflict_idents, on_conflict_set)
        else:
            conflict_action = sql.SQL("ON CONFLICT ({}) DO NOTHING").format(conflict_idents)
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) {}").format(
            table_ident, column_idents, placeholders, conflict_action
        )
        query_str = self._storage.query_str(query)
        rows = [[rid] + vals for rid, vals in zip(ids, data, strict=True)]
        with self.with_tx():
            self._storage.execute_batch(query_str, rows)
            pgc_rows = self._storage.query(
                "SELECT DISTINCT pgc FROM layer0.records WHERE id = ANY(%s) AND pgc IS NOT NULL",
                params=[ids],
            )
            touch_pgcs(self._storage, [int(row["pgc"]) for row in pgc_rows])

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
        by_id = {
            r["record_id"]: model.ICRSRecord(
                ra=float(r["ra"]),
                e_ra=float(r["e_ra"]),
                dec=float(r["dec"]),
                e_dec=float(r["e_dec"]),
            )
            for r in rows
        }
        return [by_id.get(rid) for rid in record_ids]

    def get_redshift_records(self, record_ids: list[str]) -> list[model.RedshiftRecord | None]:
        if not record_ids:
            return []
        rows = self._storage.query(
            "SELECT record_id, cz, e_cz FROM cz.data WHERE record_id = ANY(%s)",
            params=[record_ids],
        )
        units = self.get_column_units(model.RawCatalog.REDSHIFT)
        default_e_cz = float(DEFAULT_E_CZ.to_value(u.Unit(units["e_cz"])))
        by_id = {
            r["record_id"]: model.RedshiftRecord(
                cz=float(r["cz"]),
                e_cz=float(r["e_cz"]) if r["e_cz"] is not None else default_e_cz,
            )
            for r in rows
        }
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

    def query_records(
        self,
        catalogs: list[model.RawCatalog],
        record_ids: list[str] | None = None,
        table_name: str | None = None,
        offset: str | None = None,
        limit: int | None = None,
    ) -> list[model.Record]:
        if not catalogs:
            return []

        readable: list[tuple[model.RawCatalog, type[model.CatalogObject], list[str]]] = []
        for catalog in catalogs:
            object_cls = model.get_catalog_object_type(catalog)
            try:
                keys = object_cls.layer1_keys()
            except NotImplementedError:
                continue
            readable.append((catalog, object_cls, keys))

        if not readable:
            return []

        cte_parts = []
        select_parts = []
        join_parts = []
        where_conditions = []
        params = []

        for i, (catalog, object_cls, layer1_keys) in enumerate(readable):
            table_name_layer1 = object_cls.layer1_table()
            alias = f"t{i}"

            catalog_columns = []
            for column in layer1_keys:
                catalog_columns.append(f'{column} AS "{catalog.value}|{column}"')

            cte_query = f"""
            {alias} AS (
                SELECT record_id, {", ".join(catalog_columns)}
                FROM {table_name_layer1}
            """

            cte_where_conditions = []
            if record_ids:
                cte_where_conditions.append("record_id = ANY(%s)")
                params.append(record_ids)

            if cte_where_conditions:
                cte_query += f" WHERE {' AND '.join(cte_where_conditions)}"

            cte_query += ")"
            cte_parts.append(cte_query)

            select_parts.extend([f'{alias}."{catalog.value}|{column}"' for column in layer1_keys])
            select_parts.append(
                f'CASE WHEN {alias}.record_id IS NOT NULL THEN true ELSE false END AS "{catalog.value}|_present"'
            )

            if i == 0:
                join_parts.append(f"FROM {alias}")
            else:
                join_parts.append(f"FULL OUTER JOIN {alias} USING (record_id)")

        if table_name:
            where_conditions.append("layer0.records.table_id = layer0.tables.id")
            where_conditions.append("layer0.tables.table_name = %s")
            params.append(table_name)

        if offset:
            coalesce_expr = "COALESCE(" + ", ".join([f"t{i}.record_id" for i in range(len(readable))]) + ")"
            where_conditions.append(f"{coalesce_expr} > %s")
            params.append(offset)

        query = f"""
            WITH {", ".join(cte_parts)}
            SELECT COALESCE({", ".join([f"t{i}.record_id" for i in range(len(readable))])}) AS record_id,
                   {", ".join(select_parts)}
            {" ".join(join_parts)}
        """

        if table_name:
            coalesce_expr = "COALESCE(" + ", ".join([f"t{i}.record_id" for i in range(len(readable))]) + ")"
            query += f"""
            JOIN layer0.records ON {coalesce_expr} = layer0.records.id
            JOIN layer0.tables ON layer0.records.table_id = layer0.tables.id
            """

        if where_conditions:
            query += f" WHERE {' AND '.join(where_conditions)}"

        query += " ORDER BY record_id"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        records = self._storage.query(query, params=params)

        return _group_by_record_id(records, readable)


def _group_by_record_id(
    records: list[dict],
    readable: list[tuple[model.RawCatalog, type[model.CatalogObject], list[str]]],
) -> list[model.Record]:
    record_data: dict[str, list[model.CatalogObject]] = {}

    for row in records:
        record_id = row["record_id"]
        if record_id not in record_data:
            record_data[record_id] = []

        for catalog, object_cls, layer1_keys in readable:
            present_key = f"{catalog.value}|_present"
            if row.get(present_key, False):
                catalog_data = {column: row.get(f"{catalog.value}|{column}") for column in layer1_keys}

                if catalog_data:
                    catalog_object = object_cls.from_layer1(catalog_data)
                    record_data[record_id].append(catalog_object)

    result = []
    for record_id in sorted(record_data.keys()):
        result.append(model.Record(id=record_id, data=record_data[record_id]))

    return result
