import datetime

import structlog

from app.data import model
from app.lib import containers
from app.lib.storage import postgres

catalogs = [
    model.RawCatalog.ICRS,
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.REDSHIFT,
]


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def save_data(self, objects: list[model.Layer1CatalogObject]) -> None:
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

    def get_new_objects(self, dt: datetime.datetime) -> list[model.Layer1CatalogObject]:
        """
        Returns all objects that were modified since `dt`.

        TODO: make the selection in batches instead of everything at once.
        """

        objects: list[model.Layer1CatalogObject] = []

        for catalog in catalogs:
            object_cls = model.get_catalog_object_type(catalog)

            query = f"""
            SELECT * 
            FROM {object_cls.layer1_table()}
            WHERE pgc IN (
                SELECT DISTINCT pgc
                FROM {object_cls.layer1_table()}
                WHERE modification_time > %s
            )
            """

            rows = self._storage.query(query, params=[dt])
            for row in rows:
                object_id = row.pop("object_id")
                pgc = int(row.pop("pgc"))
                catalog_object = object_cls.from_layer1(row)

                objects.append(model.Layer1CatalogObject(pgc, object_id, catalog_object))

        return objects
