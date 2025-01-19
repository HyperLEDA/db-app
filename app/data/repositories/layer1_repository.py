import itertools

import structlog

from app.data import model
from app.lib.storage import postgres

tables: dict[model.Layer1Catalog, str] = {
    model.Layer1Catalog.ICRS: "icrs.data",
    model.Layer1Catalog.DESIGNATION: "designation.data",
}


class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def save_data(self, catalog: model.Layer1Catalog, objects: list[model.Layer1CatalogObject]) -> None:
        table = tables[model.Layer1Catalog(catalog)]
        self._logger.info("Saving data to layer 1", table=table)

        unique_columns = set()

        for obj in objects:
            unique_columns.update(obj.data.keys())

        column_names = ["pgc", "object_id"] + list(unique_columns)
        values = []

        for obj in objects:
            row_values = [obj.pgc, obj.object_id]

            for column in unique_columns:
                row_values.append(obj.data.get(column, None))
            values.append(tuple(row_values))

        placeholders = ",".join(["%s"] * len(column_names))
        query = f"""
        INSERT INTO {table} ({", ".join(column_names)}) 
        VALUES {", ".join(["(" + placeholders + ")"] * len(objects))}
        """

        self._storage.exec(query, params=list(itertools.chain.from_iterable(values)))
