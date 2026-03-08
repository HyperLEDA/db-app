import datetime
from typing import Any

import structlog

from app.data import model
from app.lib import containers
from app.lib.storage import postgres


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def get_column_units(self, catalog: model.RawCatalog) -> dict[str, str]:
        object_cls = model.get_catalog_object_type(catalog)
        schema, table_name = object_cls.layer1_table().split(".")
        rows = self._storage.query(
            "SELECT column_name, param->>'unit' as unit FROM meta.column_info "
            "WHERE schema_name = %s AND table_name = %s AND param->>'unit' IS NOT NULL",
            params=[schema, table_name],
        )
        return {row["column_name"]: row["unit"] for row in rows}

    def save_structured_data(self, table: str, columns: list[str], ids: list[str], data: list[list[Any]]) -> None:
        all_columns = ["record_id"] + columns
        placeholders = ",".join(["%s"] * len(all_columns))
        on_conflict = ", ".join(f"{c} = EXCLUDED.{c}" for c in all_columns)
        query = (
            f"INSERT INTO {table} ({', '.join(all_columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT (record_id) DO UPDATE SET {on_conflict}"
        )
        rows = [[rid] + vals for rid, vals in zip(ids, data, strict=True)]
        with self.with_tx():
            self._storage.execute_batch(query, rows)

    def save_data(self, records: list[model.Record]) -> None:
        all_catalog_objects = []
        for record in records:
            for catalog_object in record.data:
                all_catalog_objects.append((record.id, catalog_object))

        table_objects = containers.group_by(all_catalog_objects, lambda item: item[1].layer1_table())

        with self.with_tx():
            for table, table_items in table_objects.items():
                if not table_items:
                    continue

                columns = ["record_id"]
                columns.extend(table_items[0][1].layer1_keys())

                params = []
                values = []
                for record_id, catalog_object in table_items:
                    data = catalog_object.layer1_data()
                    data["record_id"] = record_id

                    params.extend([data[column] for column in columns])
                    values.append(",".join(["%s"] * len(columns)))

                on_conflict_update_statement = ", ".join([f"{column} = EXCLUDED.{column}" for column in columns])

                query = f"""
                INSERT INTO {table} ({", ".join(columns)}) 
                VALUES {", ".join([f"({value})" for value in values])}
                ON CONFLICT (record_id) DO UPDATE SET {on_conflict_update_statement}
                """

                self._storage.exec(query, params=params)

                self._logger.debug(
                    "Saved data to layer 1",
                    table=table,
                    object_count=len(table_items),
                )

    def get_new_nature_records(
        self, dt: datetime.datetime, limit: int, offset: int
    ) -> list[model.StructuredData[model.NatureRecord]]:
        query = """SELECT o.pgc, l1.record_id, l1.type_name
        FROM nature.data AS l1
        JOIN layer0.records AS o ON l1.record_id = o.id
        WHERE o.pgc IN (
            SELECT DISTINCT o.pgc
            FROM nature.data AS l1
            JOIN layer0.records AS o ON l1.record_id = o.id
            WHERE o.modification_time > %s AND o.pgc > %s
            ORDER BY o.pgc
            LIMIT %s
        )
        ORDER BY o.pgc ASC"""
        rows = self._storage.query(query, params=[dt, offset, limit])
        return [
            model.StructuredData(
                pgc=int(r["pgc"]),
                record_id=r["record_id"],
                data=model.NatureRecord(type_name=r["type_name"]),
            )
            for r in rows
        ]

    def get_new_icrs_records(
        self, dt: datetime.datetime, limit: int, offset: int
    ) -> list[model.StructuredData[model.ICRSRecord]]:
        query = """SELECT o.pgc, l1.record_id, l1.ra, l1.e_ra, l1.dec, l1.e_dec
        FROM icrs.data AS l1
        JOIN layer0.records AS o ON l1.record_id = o.id
        WHERE o.pgc IN (
            SELECT DISTINCT o.pgc
            FROM icrs.data AS l1
            JOIN layer0.records AS o ON l1.record_id = o.id
            WHERE o.modification_time > %s AND o.pgc > %s
            ORDER BY o.pgc
            LIMIT %s
        )
        ORDER BY o.pgc ASC"""
        rows = self._storage.query(query, params=[dt, offset, limit])
        return [
            model.StructuredData(
                pgc=int(r["pgc"]),
                record_id=r["record_id"],
                data=model.ICRSRecord(
                    ra=float(r["ra"]),
                    e_ra=float(r["e_ra"]),
                    dec=float(r["dec"]),
                    e_dec=float(r["e_dec"]),
                ),
            )
            for r in rows
        ]

    def get_new_redshift_records(
        self, dt: datetime.datetime, limit: int, offset: int
    ) -> list[model.StructuredData[model.RedshiftRecord]]:
        query = """SELECT o.pgc, l1.record_id, l1.cz, l1.e_cz
        FROM cz.data AS l1
        JOIN layer0.records AS o ON l1.record_id = o.id
        WHERE o.pgc IN (
            SELECT DISTINCT o.pgc
            FROM cz.data AS l1
            JOIN layer0.records AS o ON l1.record_id = o.id
            WHERE o.modification_time > %s AND o.pgc > %s
            ORDER BY o.pgc
            LIMIT %s
        )
        ORDER BY o.pgc ASC"""
        rows = self._storage.query(query, params=[dt, offset, limit])
        return [
            model.StructuredData(
                pgc=int(r["pgc"]),
                record_id=r["record_id"],
                data=model.RedshiftRecord(
                    cz=float(r["cz"]),
                    e_cz=float(r["e_cz"]),
                ),
            )
            for r in rows
        ]

    def get_new_designation_records(
        self, dt: datetime.datetime, limit: int, offset: int
    ) -> list[model.StructuredData[model.DesignationRecord]]:
        query = """SELECT o.pgc, l1.record_id, l1.design
        FROM designation.data AS l1
        JOIN layer0.records AS o ON l1.record_id = o.id
        WHERE o.pgc IN (
            SELECT DISTINCT o.pgc
            FROM designation.data AS l1
            JOIN layer0.records AS o ON l1.record_id = o.id
            WHERE o.modification_time > %s AND o.pgc > %s
            ORDER BY o.pgc
            LIMIT %s
        )
        ORDER BY o.pgc ASC"""
        rows = self._storage.query(query, params=[dt, offset, limit])
        return [
            model.StructuredData(
                pgc=int(r["pgc"]),
                record_id=r["record_id"],
                data=model.DesignationRecord(design=r["design"]),
            )
            for r in rows
        ]

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

        cte_parts = []
        select_parts = []
        join_parts = []
        where_conditions = []
        params = []

        for i, catalog in enumerate(catalogs):
            object_cls = model.get_catalog_object_type(catalog)
            table_name_layer1 = object_cls.layer1_table()
            alias = f"t{i}"

            catalog_columns = []
            for column in object_cls.layer1_keys():
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

            select_parts.extend([f'{alias}."{catalog.value}|{column}"' for column in object_cls.layer1_keys()])
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
            coalesce_expr = "COALESCE(" + ", ".join([f"t{i}.record_id" for i in range(len(catalogs))]) + ")"
            where_conditions.append(f"{coalesce_expr} > %s")
            params.append(offset)

        query = f"""
            WITH {", ".join(cte_parts)}
            SELECT COALESCE({", ".join([f"t{i}.record_id" for i in range(len(catalogs))])}) AS record_id,
                   {", ".join(select_parts)}
            {" ".join(join_parts)}
        """

        if table_name:
            coalesce_expr = "COALESCE(" + ", ".join([f"t{i}.record_id" for i in range(len(catalogs))]) + ")"
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

        return self._group_by_record_id(records, catalogs)

    def _group_by_record_id(self, records: list[dict], catalogs: list[model.RawCatalog]) -> list[model.Record]:
        record_data: dict[str, list[model.CatalogObject]] = {}

        for row in records:
            record_id = row["record_id"]
            if record_id not in record_data:
                record_data[record_id] = []

            for catalog in catalogs:
                present_key = f"{catalog.value}|_present"
                if row.get(present_key, False):
                    object_cls = model.get_catalog_object_type(catalog)

                    catalog_data = {}
                    for column in object_cls.layer1_keys():
                        catalog_data[column] = row.get(f"{catalog.value}|{column}")

                    if catalog_data:
                        catalog_object = object_cls.from_layer1(catalog_data)
                        record_data[record_id].append(catalog_object)

        result = []
        for record_id in sorted(record_data.keys()):
            result.append(model.Record(id=record_id, data=record_data[record_id]))

        return result
