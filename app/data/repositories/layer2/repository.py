import datetime
from typing import Any

import structlog
from astropy import table
from astropy import units as u
from psycopg import rows, sql

from app.data import model
from app.data.model import Layer2CatalogObject
from app.data.repositories.common import get_column_units as query_column_units
from app.lib import containers
from app.lib.storage import postgres


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
        return query_column_units(self._storage, schema, table)

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
            rows_result = self._storage.query(query)
            result[layer2_table] = [int(row["pgc"]) for row in rows_result]
        return result

    def remove_pgcs(self, catalogs: list[model.RawCatalog], pgcs: list[int]) -> None:
        if not pgcs:
            return

        for catalog in catalogs:
            object_cls = model.get_catalog_object_type(catalog)
            layer2_table = object_cls.layer2_table()
            query = f"DELETE FROM {layer2_table} WHERE pgc = ANY(%s)"
            self._storage.exec(query, params=[pgcs])

    def save(self, table_name: str, data: table.QTable) -> None:
        if len(data) == 0:
            return

        schema, relation = table_name.split(".", maxsplit=1)
        column_units = self.get_column_units(schema, relation)

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


def _column_as_list(col: Any) -> list[Any]:
    if getattr(col, "unit", None) is not None:
        return col.value.tolist()
    return [v.item() if hasattr(v, "item") else v for v in col]
