import datetime
from typing import Any

import structlog

from app.data import model
from app.data.repositories.layer2_repository import filters as repofilters
from app.lib import containers
from app.lib.storage import postgres

catalog_to_tables = {
    model.RawCatalog.ICRS: "layer2.icrs",
    model.RawCatalog.DESIGNATION: "layer2.designation",
    model.RawCatalog.REDSHIFT: "layer2.cz",
}
tables_to_catalog = {v: k for k, v in catalog_to_tables.items()}


class Layer2Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def get_last_update_time(self) -> datetime.datetime:
        return self._storage.query_one("SELECT dt FROM layer2.last_update").get("dt")

    def update_last_update_time(self, dt: datetime.datetime):
        self._storage.exec("UPDATE layer2.last_update SET dt = %s", params=[dt])

    def save_data(self, objects: list[model.Layer2CatalogObject]):
        for obj in objects:
            table = catalog_to_tables[obj.catalog_object.catalog()]

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

    def query_batch(
        self,
        catalogs: list[model.RawCatalog],
        filters: dict[str, list[repofilters.Filter]],
        limit: int,
        offset: int,
    ) -> dict[str, dict[int, list[model.CatalogObject]]]:
        """
        Queries data from the `catalogs`. `filters` is a mapping of ID to a list of filters.
        The ID is not processed in any way and is used only as a key for the output data.

        The objects are queried independently and are not joined in any way.

        Offset and limit are applied individually to each object.
        """

        columns = ["pgc"]
        table_names = []

        for catalog in catalogs:
            table_name = catalog_to_tables[catalog]
            constructor = model.get_catalog_object_type(catalog)

            table_names.append(table_name)
            columns.extend(
                [f'{table_name}.{column} AS "{catalog.value}|{column}"' for column in constructor.layer2_keys()]
            )

        joined_tables = " JOIN ".join(
            [f"{table_names[0]}"] + [f"{table_name} USING (pgc)" for table_name in table_names[1:]]
        )

        params = []
        queries = []

        for object_id, object_filters in filters.items():
            conditions = ""
            if len(filters) != 0:
                conditions = "WHERE " + " AND ".join([f.get_query() for f in object_filters])

            for f in object_filters:
                params.extend(f.get_params())

            params.append(limit)
            params.append(offset)

            curr_columns = [f"'{object_id}' AS object_id"] + columns
            query = f"SELECT {', '.join(curr_columns)} FROM {joined_tables} {conditions} LIMIT %s OFFSET %s"

            queries.append(f"({query})")

        objects = self._storage.query(" UNION ALL ".join(queries), params=params)

        objects_by_id = containers.group_by(objects, key_func=lambda obj: str(obj["object_id"]))

        result: dict[str, dict[int, list[model.CatalogObject]]] = {}

        for object_id, objects in objects_by_id.items():
            if object_id not in result:
                result[object_id] = {}

            objects_by_pgc = containers.group_by(objects, key_func=lambda obj: int(obj["pgc"]))

            for pgc, pgc_objects in objects_by_pgc.items():
                if pgc not in result[object_id]:
                    result[object_id][pgc] = []

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
                    result[object_id][pgc].append(model.new_catalog_object(catalog, **data))

        return result

    def query(
        self,
        catalogs: list[model.RawCatalog],
        filters: list[repofilters.Filter],
        limit: int,
        offset: int,
    ) -> dict[int, list[model.CatalogObject]]:
        res = self.query_batch(catalogs, {"obj": filters}, limit, offset)
        return res["obj"]
