import datetime

import structlog

from app.data import model
from app.lib import containers
from app.lib.storage import postgres


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

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

    def get_new_observations(
        self, dt: datetime.datetime, limit: int, offset: int, catalog: model.RawCatalog
    ) -> list[model.RecordWithPGC]:
        """
        Returns all objects that were modified since `dt`.
        `limit` is the number of PGC numbers to select, not the final number of objects.
        As such, this function will return around
        `limit * (average_number_of_observations_per_PGC)` objects, not `limit`.

        `offset` is the first PGC number from which to start selecting.

        This makes the function safe for aggregation - for each returned PGC all of its objects will be returned.
        """
        object_cls = model.get_catalog_object_type(catalog)

        query = f"""SELECT *
        FROM {object_cls.layer1_table()} AS l1
        JOIN layer0.records AS o ON l1.record_id = o.id
        WHERE o.pgc IN (
            SELECT DISTINCT o.pgc
            FROM {object_cls.layer1_table()} AS l1
            JOIN layer0.records AS o ON l1.record_id = o.id
            WHERE o.modification_time > %s AND o.pgc > %s
            ORDER BY o.pgc
            LIMIT %s
        )
        ORDER BY o.pgc ASC"""

        rows = self._storage.query(query, params=[dt, offset, limit])

        record_data: dict[tuple[int, str], list[model.CatalogObject]] = {}

        for row in rows:
            record_id = row.pop("record_id")
            pgc = int(row.pop("pgc"))
            catalog_object = object_cls.from_layer1(row)

            key = (pgc, record_id)
            if key not in record_data:
                record_data[key] = []
            record_data[key].append(catalog_object)

        records: list[model.RecordWithPGC] = []
        for (pgc, record_id), catalog_objects in record_data.items():
            record_info = model.Record(id=record_id, data=catalog_objects)
            records.append(model.RecordWithPGC(pgc, record_info))

        return records

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
