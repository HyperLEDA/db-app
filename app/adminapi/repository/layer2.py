from typing import Any

import structlog
from psycopg import rows

from app.data import model
from app.data.model import Layer2CatalogObject
from app.lib import containers
from app.lib.storage import postgres


class Layer2Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

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

        query_params = [pgc_numbers] * len(catalogs) + [limit, offset]

        objects = self._storage.query(query, params=query_params)

        return _group_by_pgc(objects)


def _group_by_pgc(objects: list[rows.DictRow]) -> list[model.Layer2CatalogObject]:
    objects_by_pgc = containers.group_by(objects, key_func=lambda obj: int(obj["pgc"]))
    result = []

    for pgc, pgc_objects in objects_by_pgc.items():
        layer2_obj = model.Layer2CatalogObject(pgc, [])

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

            if presence_flags.get(catalog, False):
                layer2_obj.data.append(object_cls.from_layer2(data))

        result.append(layer2_obj)

    return result
