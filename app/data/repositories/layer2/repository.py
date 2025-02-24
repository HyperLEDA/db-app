import datetime
import json
from typing import Any

import structlog

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

    def get_last_update_time(self) -> datetime.datetime:
        return self._storage.query_one("SELECT dt FROM layer2.last_update")["dt"]

    def update_last_update_time(self, dt: datetime.datetime):
        self._storage.exec("UPDATE layer2.last_update SET dt = %s", params=[dt])

    def save_data(self, objects: list[model.Layer2CatalogObject]):
        for obj in objects:
            # TODO: batch inserts grouped by table
            table = obj.catalog_object.layer2_table()

            data = obj.catalog_object.layer2_data()
            data["pgc"] = obj.pgc
            columns = list(data.keys())
            values = [data[column] for column in columns]

            query = f"""
            INSERT INTO {table} ({", ".join(columns)}) 
            VALUES ({",".join(["%s"] * len(columns))})
            ON CONFLICT (pgc) DO UPDATE SET {", ".join([f"{column} = EXCLUDED.{column}" for column in columns])}
            """

            self._storage.exec(query, params=values)

    def _construct_batch_query(
        self,
        catalogs: list[model.RawCatalog],
        search_types: dict[str, repofilters.Filter],
        search_params: dict[str, params.SearchParams],
        limit: int,
        offset: int,
    ) -> tuple[str, list[Any]]:
        query = """
            WITH search_params AS (
                SELECT * FROM (
                    VALUES 
                        {values}
                ) AS t(object_id, search_type, params)
            ) 
            SELECT sp.object_id, pgc, {columns}
            FROM search_params sp
            CROSS JOIN {joined_tables}
            WHERE {conditions}
            LIMIT %s OFFSET %s
        """

        values_lines = []
        params = []

        for object_id, sparams in search_params.items():
            values_lines.append("(%s, %s, %s::jsonb)")
            params.extend([object_id, sparams.name(), json.dumps(sparams.get_params())])

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
        search_types: dict[str, repofilters.Filter],
        search_params: dict[str, params.SearchParams],
        limit: int,
        offset: int,
    ) -> dict[str, list[model.Layer2Object]]:
        query, params = self._construct_batch_query(catalogs, search_types, search_params, limit, offset)

        objects = self._storage.query(query, params=params)

        objects_by_id = containers.group_by(objects, key_func=lambda obj: str(obj["object_id"]))

        result: dict[str, list[model.Layer2Object]] = {}

        for object_id, objects in objects_by_id.items():
            if object_id not in result:
                result[object_id] = []

            objects_by_pgc = containers.group_by(objects, key_func=lambda obj: int(obj["pgc"]))

            for pgc, pgc_objects in objects_by_pgc.items():
                layer2_obj = model.Layer2Object(pgc, [])

                # TODO: what if for each pgc there are multiple rows? For example, if
                # the catalog does not have a UNIQUE constraint on pgc.
                obj = pgc_objects[0]
                obj.pop("object_id")
                obj.pop("pgc")

                res: dict[model.RawCatalog, dict[str, Any]] = {}

                for key, value in obj.items():
                    catalog_name, column = key.split("|")
                    catalog = model.RawCatalog(catalog_name)

                    if catalog not in res:
                        res[catalog] = {}

                    res[catalog][column] = value

                for catalog, data in res.items():
                    object_cls = model.get_catalog_object_type(catalog)

                    layer2_obj.data.append(object_cls.from_layer2(data))

                result[object_id].append(layer2_obj)

        return result

    def query(
        self,
        catalogs: list[model.RawCatalog],
        filters: repofilters.Filter,
        search_params: params.SearchParams,
        limit: int,
        offset: int,
    ) -> list[model.Layer2Object]:
        res = self.query_batch(catalogs, {search_params.name(): filters}, {"obj": search_params}, limit, offset)
        return res["obj"]
