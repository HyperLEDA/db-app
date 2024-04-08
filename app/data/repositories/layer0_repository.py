from typing import Any, final

import psycopg
import structlog

from app.data import interface, postgres_storage, template


@final
class Layer0Repository(interface.Layer0Repository):
    def __init__(self, storage: postgres_storage.Storage, logger: structlog.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def with_tx(self) -> psycopg.Transaction:
        return self._storage.with_tx()

    def create_table(
        self,
        schema: str,
        name: str,
        fields: list[tuple[str, str]],
        tx: psycopg.Transaction | None = None,
    ) -> None:
        self._storage.exec(
            template.CREATE_TABLE.render(
                schema=schema,
                name=name,
                fields=fields,
            ),
            [],
            tx,
        )

    def insert_raw_data(
        self, schema: str, table_name: str, raw_data: list[dict[str, Any]], tx: psycopg.Transaction | None = None
    ) -> None:
        """
        This method puts everything in parameters for prepared statement. This should not be a big
        issue but one would be better off using this function in batches since prepared statement make
        this quite cheap (excluding network slow down, though).

        Also the contract of this method requires all dicts to have the same set of keys.
        """
        if not raw_data:
            self._logger.warn("trying to insert 0 rows into the table", table=f"{schema}.{table_name}")
            return

        params = []
        objects = []
        fields = raw_data[0].keys()

        for row in raw_data:
            obj = {}
            for field in fields:
                value = row[field]
                try:
                    params.append(value.item())
                except AttributeError:
                    params.append(value)
                obj[field] = "%s"

            objects.append(obj)

        query = template.INSERT_RAW_DATA.render(schema=schema, table=table_name, fields=fields, objects=objects)

        self._storage.exec(
            query,
            params,
            tx,
        )
