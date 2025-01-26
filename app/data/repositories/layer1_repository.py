import datetime

import structlog

from app.data import model
from app.lib.storage import postgres

tables: dict[model.RawCatalog, str] = {
    model.RawCatalog.ICRS: "icrs.data",
    model.RawCatalog.DESIGNATION: "designation.data",
}


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def save_data(self, objects: list[model.CatalogObject]) -> None:
        """
        For each object, saves it to corresponding catalog in the storage.
        Object has no knowledge of the table name of the catalog it belongs to.

        `objects` is a list since it is more efficient to save multiple objects in one insert into catalog.
        For now, objects are saved one by one but the `list` allows for future optimizations.
        """

        for obj in objects:
            catalog = obj.catalog()
            table = tables[catalog]

            self._logger.info("Saving data to layer 1", table=table, pgc=obj.pgc())

            data = obj.layer1_data()
            columns = list(data.keys())
            values = [data[column] for column in columns]

            query = f"""
            INSERT INTO {table} ({", ".join(columns)}) 
            VALUES ({",".join(["%s"] * len(columns))})
            """

            self._storage.exec(query, params=values)

    def get_new_objects(self, dt: datetime.datetime) -> list[model.CatalogObject]:
        """
        Returns all objects that were modified since `dt`.

        TODO: make the selection in batches instead of everything at once.
        """

        objects: list[model.CatalogObject] = []

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
                objects.append(model.get_catalog_object_type(catalog)(**row))

        return objects
