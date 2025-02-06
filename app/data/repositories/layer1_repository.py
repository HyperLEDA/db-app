import datetime

import structlog

from app.data import model
from app.lib.storage import postgres

tables: dict[model.RawCatalog, str] = {
    model.RawCatalog.ICRS: "icrs.data",
    model.RawCatalog.DESIGNATION: "designation.data",
    model.RawCatalog.REDSHIFT: "cz.data",
}


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def save_data(self, objects: list[model.Layer1CatalogObject]) -> None:
        """
        For each object, saves it to corresponding catalog in the storage.
        Object has no knowledge of the table name of the catalog it belongs to.

        `objects` is a list since it is more efficient to save multiple objects in one insert into catalog.
        For now, objects are saved one by one but the `list` allows for future optimizations.
        """

        for layer1_obj in objects:
            catalog = layer1_obj.catalog_object.catalog()
            table = tables[catalog]

            self._logger.info("Saving data to layer 1", table=table, pgc=layer1_obj.pgc)

            data = layer1_obj.catalog_object.layer1_data()
            data["pgc"] = layer1_obj.pgc
            data["object_id"] = layer1_obj.object_id

            columns = list(data.keys())
            values = [data[column] for column in columns]

            query = f"""
            INSERT INTO {table} ({", ".join(columns)}) 
            VALUES ({",".join(["%s"] * len(columns))})
            """

            self._storage.exec(query, params=values)

    def get_new_objects(self, dt: datetime.datetime) -> list[model.Layer1CatalogObject]:
        """
        Returns all objects that were modified since `dt`.

        TODO: make the selection in batches instead of everything at once.
        """

        objects: list[model.Layer1CatalogObject] = []

        for catalog, table in tables.items():
            query = f"""
            SELECT * 
            FROM {table}
            WHERE pgc IN (
                SELECT DISTINCT pgc
                FROM {table}
                WHERE modification_time > %s
            )
            """

            rows = self._storage.query(query, params=[dt])
            for row in rows:
                object_id = row.pop("object_id")
                pgc = int(row.pop("pgc"))
                catalog_object = model.new_catalog_object(catalog, **row)

                objects.append(model.Layer1CatalogObject(pgc, object_id, catalog_object))

        return objects
