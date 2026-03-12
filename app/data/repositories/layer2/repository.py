import datetime
import json
from collections.abc import Mapping
from typing import Any

import structlog
from psycopg import rows

from app.data import model
from app.data.model import Layer2CatalogObject, Layer2Object
from app.data.model import layer2 as layer2_model
from app.data.repositories.layer2 import filters as repofilters
from app.data.repositories.layer2 import params
from app.lib import concurrency, containers
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

    def query_catalogs_batch(
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

    def _query_designations(self, pgcs: list[int]) -> dict[int, layer2_model.DesignationCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, design FROM layer2.designation WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {int(row["pgc"]): layer2_model.DesignationCatalog(name=str(row["design"])) for row in rows}

    def _query_icrs(self, pgcs: list[int]) -> dict[int, layer2_model.ICRSCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, ra, e_ra, dec, e_dec FROM layer2.icrs WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        result: dict[int, layer2_model.ICRSCatalog] = {}
        for row in rows:
            if all(row.get(k) is not None for k in ("ra", "e_ra", "dec", "e_dec")):
                result[int(row["pgc"])] = layer2_model.ICRSCatalog(
                    ra=float(row["ra"]),
                    e_ra=float(row["e_ra"]),
                    dec=float(row["dec"]),
                    e_dec=float(row["e_dec"]),
                )
        return result

    def _query_redshift(self, pgcs: list[int]) -> dict[int, layer2_model.RedshiftCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, cz, e_cz FROM layer2.cz WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {
            int(row["pgc"]): layer2_model.RedshiftCatalog(cz=float(row["cz"]), e_cz=float(row["e_cz"]))
            for row in rows
            if row.get("cz") is not None and row.get("e_cz") is not None
        }

    def _query_nature(self, pgcs: list[int]) -> dict[int, layer2_model.NatureCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, type_name FROM layer2.nature WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {
            int(row["pgc"]): layer2_model.NatureCatalog(type_name=str(row["type_name"]))
            for row in rows
            if row.get("type_name") is not None
        }

    def query_pgc(
        self,
        catalogs: list[model.RawCatalog],
        pgc_numbers: list[int],
        limit: int,
        offset: int = 0,
    ) -> list[Layer2Object]:
        if not catalogs or not pgc_numbers:
            return []

        pgcs_page = sorted(pgc_numbers)[offset : offset + limit]
        if not pgcs_page:
            return []

        errgr = concurrency.ErrorGroup()
        designation_task: concurrency.TaskResult[dict[int, layer2_model.DesignationCatalog]] | None = None
        icrs_task: concurrency.TaskResult[dict[int, layer2_model.ICRSCatalog]] | None = None
        redshift_task: concurrency.TaskResult[dict[int, layer2_model.RedshiftCatalog]] | None = None
        nature_task: concurrency.TaskResult[dict[int, layer2_model.NatureCatalog]] | None = None

        if model.RawCatalog.DESIGNATION in catalogs:
            designation_task = errgr.run(self._query_designations, pgcs_page)
        if model.RawCatalog.ICRS in catalogs:
            icrs_task = errgr.run(self._query_icrs, pgcs_page)
        if model.RawCatalog.REDSHIFT in catalogs:
            redshift_task = errgr.run(self._query_redshift, pgcs_page)
        if model.RawCatalog.NATURE in catalogs:
            nature_task = errgr.run(self._query_nature, pgcs_page)

        errgr.wait()

        designation_map = designation_task.result() if designation_task is not None else {}
        icrs_map = icrs_task.result() if icrs_task is not None else {}
        redshift_map = redshift_task.result() if redshift_task is not None else {}
        nature_map = nature_task.result() if nature_task is not None else {}

        return [
            self._layer2_object_from_maps(pgc, catalogs, designation_map, icrs_map, redshift_map, nature_map)
            for pgc in pgcs_page
        ]

    def _layer2_object_from_maps(
        self,
        pgc: int,
        catalogs: list[model.RawCatalog],
        designation_map: dict[int, layer2_model.DesignationCatalog],
        icrs_map: dict[int, layer2_model.ICRSCatalog],
        redshift_map: dict[int, layer2_model.RedshiftCatalog],
        nature_map: dict[int, layer2_model.NatureCatalog],
    ) -> Layer2Object:
        designation = designation_map.get(pgc) if model.RawCatalog.DESIGNATION in catalogs else None
        icrs = icrs_map.get(pgc) if model.RawCatalog.ICRS in catalogs else None
        redshift = redshift_map.get(pgc) if model.RawCatalog.REDSHIFT in catalogs else None
        nature = nature_map.get(pgc) if model.RawCatalog.NATURE in catalogs else None

        return Layer2Object(
            pgc=pgc,
            catalogs=layer2_model.Catalogs(
                designation=designation,
                icrs=icrs,
                redshift=redshift,
                nature=nature,
            ),
        )

    def query_catalogs_pgc(
        self,
        catalogs: list[model.RawCatalog],
        pgc_numbers: list[int],
        limit: int,
        offset: int = 0,
    ) -> list[Layer2CatalogObject]:
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

    def query_catalogs(
        self,
        catalogs: list[model.RawCatalog],
        filters: repofilters.Filter,
        search_params: params.SearchParams,
        limit: int,
        offset: int,
    ) -> list[model.Layer2CatalogObject]:
        res = self.query_catalogs_batch(
            catalogs, {search_params.name(): filters}, {"obj": search_params}, limit, offset
        )

        if "obj" not in res:
            return []

        return res["obj"]
