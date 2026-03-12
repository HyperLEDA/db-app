import datetime
import json
from collections.abc import Mapping
from typing import Any

import structlog
from psycopg import rows

from app.data import model
from app.data.repositories.layer2 import filters as repofilters
from app.data.repositories.layer2 import params
from app.lib import containers
from app.lib.storage import postgres

catalogs = [
    model.RawCatalog.ICRS,
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.REDSHIFT,
]


class Layer2Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def get_last_update_time(self, catalog: model.RawCatalog) -> datetime.datetime:
        return self._storage.query_one("SELECT dt FROM layer2.last_update WHERE catalog = %s", params=[catalog.value])[
            "dt"
        ]

    def update_last_update_time(self, dt: datetime.datetime, catalog: model.RawCatalog) -> None:
        self._storage.exec(
            "UPDATE layer2.last_update SET dt = %s WHERE catalog = %s",
            params=[dt, catalog.value],
        )

    def get_column_units(self, schema: str, table: str) -> dict[str, str]:
        rows = self._storage.query(
            "SELECT column_name, param->>'unit' as unit FROM meta.column_info "
            "WHERE schema_name = %s AND table_name = %s AND param->>'unit' IS NOT NULL",
            params=[schema, table],
        )
        return {row["column_name"]: row["unit"] for row in rows}

    def get_orphaned_pgcs(self, catalogs: list[model.RawCatalog]) -> dict[str, list[int]]:
        result: dict[str, list[int]] = {}
        for catalog in catalogs:
            object_cls = model.get_catalog_object_type(catalog)
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
            rows = self._storage.query(query)
            result[layer2_table] = [int(row["pgc"]) for row in rows]
        return result

    def remove_pgcs(self, catalogs: list[model.RawCatalog], pgcs: list[int]) -> None:
        if not pgcs:
            return

        for catalog in catalogs:
            object_cls = model.get_catalog_object_type(catalog)
            layer2_table = object_cls.layer2_table()
            query = f"DELETE FROM {layer2_table} WHERE pgc = ANY(%s)"
            self._storage.exec(query, params=[pgcs])

    def save(self, table: str, columns: list[str], pgcs: list[int], data: list[list[Any]]) -> None:
        if not pgcs:
            return
        all_columns = ["pgc"] + columns
        placeholders = ",".join(["%s"] * len(all_columns))
        on_conflict = ", ".join([f"{c} = EXCLUDED.{c}" for c in all_columns])
        query = (
            f"INSERT INTO {table} ({', '.join(all_columns)}) VALUES ({placeholders}) "
            f"ON CONFLICT (pgc) DO UPDATE SET {on_conflict}"
        )
        rows = [[pgc, *row] for pgc, row in zip(pgcs, data, strict=True)]
        with self.with_tx():
            self._storage.execute_batch(query, rows)

    def _construct_batch_query(
        self,
        catalogs: list[model.RawCatalog],
        search_types: Mapping[str, repofilters.Filter],
        search_params: Mapping[str, params.SearchParams],
        limit: int,
        offset: int,
    ) -> tuple[str, list[Any]]:
        if not search_params:
            # If no search parameters, return empty result
            return "SELECT NULL as record_id, NULL as pgc WHERE FALSE", []

        query = """
            WITH search_params AS (
                SELECT * FROM (
                    VALUES 
                        {values}
                ) AS t(record_id, search_type, params)
            ) 
            SELECT sp.record_id, pgc, {columns}
            FROM search_params sp
            CROSS JOIN {joined_tables}
            WHERE {conditions}
            LIMIT %s OFFSET %s
        """

        values_lines = []
        params = []

        for record_id, sparams in search_params.items():
            values_lines.append("(%s, %s, %s::jsonb)")
            params.extend([record_id, sparams.name(), json.dumps(sparams.get_params())])

        columns = []
        table_names = []

        for catalog in catalogs:
            object_cls = model.get_catalog_object_type(catalog)

            table_names.append(object_cls.layer2_table())
            columns.extend(
                [
                    f'{object_cls.layer2_table()}.{column} AS "{catalog.value}|{column}"'
                    for column in object_cls.layer2_keys()
                ]
            )
            columns.append(
                f"CASE WHEN {object_cls.layer2_table()}.pgc IS NOT NULL "
                f'THEN true ELSE false END AS "{catalog.value}|_present"'
            )

        joined_tables = " FULL JOIN ".join(
            [f"{table_names[0]}"] + [f"{table_name} USING (pgc)" for table_name in table_names[1:]]
        )

        condition_statements = []

        for search_type, search_filter in search_types.items():
            condition_statements.append(f"(sp.search_type = '{search_type}' AND {search_filter.get_query()})")
            params.extend(search_filter.get_params())

        params.extend([limit, offset])

        return query.format(
            values=",".join(values_lines),
            columns=",".join(columns),
            joined_tables=joined_tables,
            conditions=" OR ".join(condition_statements),
        ), params

    def query_batch(
        self,
        catalogs: list[model.RawCatalog],
        search_types: Mapping[str, repofilters.Filter],
        search_params: Mapping[str, params.SearchParams],
        limit: int,
        offset: int,
    ) -> dict[str, list[model.Layer2CatalogObject]]:
        query, params = self._construct_batch_query(catalogs, search_types, search_params, limit, offset)

        records = self._storage.query(query, params=params)

        records_by_id = containers.group_by(records, key_func=lambda obj: str(obj["record_id"]))

        result: dict[str, list[model.Layer2CatalogObject]] = {}

        for record_id, records in records_by_id.items():
            if record_id not in result:
                result[record_id] = []

            result[record_id].extend(self._group_by_pgc(records))

        return result

    def _group_by_pgc(self, objects: list[rows.DictRow]) -> list[model.Layer2CatalogObject]:
        objects_by_pgc = containers.group_by(objects, key_func=lambda obj: int(obj["pgc"]))
        result = []

        for pgc, pgc_objects in objects_by_pgc.items():
            layer2_obj = model.Layer2CatalogObject(pgc, [])

            # TODO: what if for each pgc there are multiple rows? For example, if
            # the catalog does not have a UNIQUE constraint on pgc.
            obj = pgc_objects[0]
            if "record_id" in obj:
                obj.pop("record_id")
            if "pgc" in obj:
                obj.pop("pgc")

            res: dict[model.RawCatalog, dict[str, Any]] = {}
            presence_flags: dict[model.RawCatalog, bool] = {}

            for key, value in obj.items():
                catalog_name, column = key.split("|")
                catalog = model.RawCatalog(catalog_name)

                if column == "_present":
                    presence_flags[catalog] = bool(value)
                else:
                    if catalog not in res:
                        res[catalog] = {}
                    res[catalog][column] = value

            for catalog, data in res.items():
                object_cls = model.get_catalog_object_type(catalog)

                # Only create catalog object if the object exists in this table
                if presence_flags.get(catalog, False):
                    layer2_obj.data.append(object_cls.from_layer2(data))

            result.append(layer2_obj)

        return result

    def query_pgc(
        self,
        catalogs: list[model.RawCatalog],
        pgc_numbers: list[int],
        limit: int,
        offset: int = 0,
    ):
        if not catalogs:
            return []

        cte_parts = []
        select_parts = []
        join_parts = []

        for i, catalog in enumerate(catalogs):
            object_cls = model.get_catalog_object_type(catalog)
            table_name = object_cls.layer2_table()
            alias = f"t{i}"

            catalog_columns = []
            for column in object_cls.layer2_keys():
                catalog_columns.append(f'{column} AS "{catalog.value}|{column}"')

            cte_parts.append(f"""
            {alias} AS (
                SELECT pgc, {", ".join(catalog_columns)}
                FROM {table_name}
                WHERE pgc = ANY(%s)
            )""")

            select_parts.extend([f'{alias}."{catalog.value}|{column}"' for column in object_cls.layer2_keys()])
            select_parts.append(
                f'CASE WHEN {alias}.pgc IS NOT NULL THEN true ELSE false END AS "{catalog.value}|_present"'
            )

            if i == 0:
                join_parts.append(f"FROM {alias}")
            else:
                join_parts.append(f"FULL OUTER JOIN {alias} USING (pgc)")

        query = f"""
            WITH {", ".join(cte_parts)}
            SELECT COALESCE({", ".join([f"t{i}.pgc" for i in range(len(catalogs))])}) AS pgc,
                   {", ".join(select_parts)}
            {" ".join(join_parts)}
            ORDER BY pgc
            LIMIT %s OFFSET %s
        """

        params = [pgc_numbers] * len(catalogs) + [limit, offset]

        objects = self._storage.query(query, params=params)

        return self._group_by_pgc(objects)

    def query(
        self,
        catalogs: list[model.RawCatalog],
        filters: repofilters.Filter,
        search_params: params.SearchParams,
        limit: int,
        offset: int,
    ) -> list[model.Layer2CatalogObject]:
        res = self.query_batch(catalogs, {search_params.name(): filters}, {"obj": search_params}, limit, offset)

        if "obj" not in res:
            return []

        return res["obj"]
