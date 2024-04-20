import json
from typing import final

import psycopg
import structlog

from app.data import interface, model, template
from app.lib.storage import postgres

RAWDATA_SCHEMA = "rawdata"


@final
class Layer0Repository(interface.Layer0Repository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def with_tx(self) -> psycopg.Transaction:
        return self._storage.with_tx()

    def create_table(self, data: model.Layer0Creation, tx: psycopg.Transaction | None = None) -> str:
        """
        Creates table, writes metadata and returns string that identifies the table for
        further requests.
        """
        # TODO: use tx or new transaction here
        fields = []
        comment_queries = []

        for column_descr in data.column_descriptions:
            fields.append((column_descr.name, column_descr.data_type))
            comment_queries.append(
                template.render_query(
                    template.ADD_COLUMN_COMMENT,
                    schema=RAWDATA_SCHEMA,
                    table_name=data.table_name,
                    column_name=column_descr.name,
                    params=json.dumps(
                        {
                            "description": column_descr.description,
                            "unit": column_descr.unit,
                        }
                    ),
                )
            )

        self._storage.exec(
            template.render_query(
                template.CREATE_TABLE,
                schema=RAWDATA_SCHEMA,
                name=data.table_name,
                fields=fields,
            )
        )

        if data.comment is not None:
            self._storage.exec(
                template.render_query(
                    template.ADD_TABLE_COMMENT,
                    schema=RAWDATA_SCHEMA,
                    table_name=data.table_name,
                    params=json.dumps({"description": data.comment}),
                ),
                tx=tx,
            )

        for query in comment_queries:
            self._storage.exec(query, tx=tx)

        rows = self._storage.exec(
            template.INSERT_TABLE_REGISTRY_ITEM,
            params=[data.bibliography_id, data.table_name, data.datatype],
            tx=tx,
        )

        return str(rows.get("id"))

    def insert_raw_data(
        self,
        data: model.Layer0RawData,
        tx: psycopg.Transaction | None = None,
    ) -> None:
        """
        This method puts everything in parameters for prepared statement. This should not be a big
        issue but one would be better off using this function in batches since prepared statement make
        this quite cheap (excluding network slow down, though).

        Also the contract of this method requires all dicts to have the same set of keys.
        """

        if len(data.data) == 0:
            self._logger.warn("trying to insert 0 rows into the table", table=f"{RAWDATA_SCHEMA}.{data.table_name}")
            return

        params = []
        objects = []
        fields = data.data.columns

        for row in data.data.to_dict(orient="records"):
            obj = {}
            for field in fields:
                value = row[field]
                params.append(value)
                obj[field] = "%s"

            objects.append(obj)

        self._storage.exec(
            template.render_query(
                template.INSERT_RAW_DATA,
                schema=RAWDATA_SCHEMA,
                table=data.table_name,
                fields=fields,
                objects=objects,
            ),
            params=params,
            tx=tx,
        )

    def table_exists(self, schema: str, table_name: str) -> bool:
        try:
            self._storage.exec(f"SELECT 1 FROM {schema}.{table_name}")
        except psycopg.errors.UndefinedTable:
            return False

        return True
