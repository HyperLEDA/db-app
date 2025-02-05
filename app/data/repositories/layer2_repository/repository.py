import datetime
from typing import Any

import structlog

from app.data import model
from app.data.repositories.layer2_repository import filters as repofilters
from app.lib.storage import postgres

catalog_to_tables = {
    model.RawCatalog.ICRS: "layer2.icrs",
    model.RawCatalog.DESIGNATION: "layer2.designation",
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

    def query(
        self,
        catalogs: list[model.RawCatalog],
        filters: list[repofilters.Filter],
        limit: int,
        offset: int,
    ) -> list[model.Layer2CatalogObject]:
        table_names = []
        columns = ["pgc"]

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

        conditions = ""
        if len(filters) != 0:
            conditions = "WHERE " + " AND ".join([f.get_query() for f in filters])

        query = f"SELECT {', '.join(columns)} FROM {joined_tables} {conditions} LIMIT %s OFFSET %s"

        params = []
        for f in filters:
            params.extend(f.get_params())

        params.append(limit)
        params.append(offset)

        objects = self._storage.query(query, params=params)

        result_objects: list[model.Layer2CatalogObject] = []

        for obj in objects:
            res: dict[model.RawCatalog, dict[str, Any]] = {}
            pgc = int(obj.pop("pgc"))

            for key, value in obj.items():
                catalog_name, column = key.split("|")
                catalog = model.RawCatalog(catalog_name)

                if catalog not in res:
                    res[catalog] = {}

                res[catalog][column] = value

            for catalog, data in res.items():
                result_objects.append(model.Layer2CatalogObject(pgc, model.new_catalog_object(catalog, **data)))

        return result_objects
