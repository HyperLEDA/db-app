import datetime

import structlog

from app.data import model
from app.lib import containers
from app.lib.storage import postgres


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def save_data(self, objects: list[model.Layer1Observation]) -> None:
        """
        For each object, saves it to corresponding catalog in the storage.

        The insertion is done efficiently - for a single table there will be only one query.
        """
        table_objects = containers.group_by(objects, lambda obj: obj.catalog_object.layer1_table())

        with self.with_tx():
            for table, table_objs in table_objects.items():
                if not table_objs:
                    continue

                columns = ["object_id"]
                columns.extend(table_objs[0].catalog_object.layer1_keys())

                params = []
                values = []
                for obj in table_objs:
                    data = obj.catalog_object.layer1_data()
                    data["object_id"] = obj.object_id

                    params.extend([data[column] for column in columns])
                    values.append(",".join(["%s"] * len(columns)))

                on_conflict_update_statement = ", ".join([f"{column} = EXCLUDED.{column}" for column in columns])

                query = f"""
                INSERT INTO {table} ({", ".join(columns)}) 
                VALUES {", ".join([f"({value})" for value in values])}
                ON CONFLICT (object_id) DO UPDATE SET {on_conflict_update_statement}
                """

                self._storage.exec(query, params=params)

                self._logger.debug(
                    "Saved data to layer 1",
                    table=table,
                    object_count=len(table_objs),
                )

    def get_new_observations(
        self, dt: datetime.datetime, limit: int, offset: int, catalog: model.RawCatalog
    ) -> list[model.Layer1PGCObservation]:
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
        JOIN rawdata.pgc AS pgc ON l1.object_id = pgc.object_id
        WHERE id IN (
            SELECT DISTINCT id
            FROM {object_cls.layer1_table()} AS l1
            JOIN rawdata.pgc AS pgc ON l1.object_id = pgc.object_id
            WHERE modification_time > %s AND pgc.id > %s
            ORDER BY id
            LIMIT %s
        )
        ORDER BY pgc.id ASC"""

        rows = self._storage.query(query, params=[dt, offset, limit])

        objects: list[model.Layer1PGCObservation] = []
        for row in rows:
            object_id = row.pop("object_id")
            pgc = int(row.pop("id"))
            catalog_object = object_cls.from_layer1(row)

            objects.append(model.Layer1PGCObservation(pgc, model.Layer1Observation(object_id, catalog_object)))

        return objects

    def get_objects_by_object_id(
        self, object_ids: list[str], catalogs: list[model.RawCatalog]
    ) -> dict[str, list[model.Layer1Observation]]:
        result: dict[str, list[model.Layer1Observation]] = {obj_id: [] for obj_id in object_ids}

        for catalog in catalogs:
            object_cls = model.get_catalog_object_type(catalog)
            table_name = object_cls.layer1_table()

            if not object_ids:
                continue

            placeholders = ",".join(["%s"] * len(object_ids))
            query = f"""
                SELECT object_id, {", ".join(object_cls.layer1_keys())}
                FROM {table_name}
                WHERE object_id IN ({placeholders})
            """

            rows = self._storage.query(query, params=object_ids)

            for row in rows:
                object_id = row["object_id"]
                catalog_object = object_cls.from_layer1(row)
                result[object_id].append(model.Layer1Observation(object_id, catalog_object))

        return result
