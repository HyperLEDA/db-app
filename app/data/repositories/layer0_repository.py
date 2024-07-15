import json
from typing import final

import psycopg
import structlog
from pandas import DataFrame

from app.data import interface, model, template
from app.data.model import ColumnDescription, Layer0Creation
from app.data.model.layer0 import CoordinatePart
from app.lib.storage import postgres
from app.lib.web.errors import DatabaseError

RAWDATA_SCHEMA = "rawdata"


@final
class Layer0Repository(interface.Layer0Repository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        self._storage = storage

    def with_tx(self) -> psycopg.Transaction:
        return self._storage.with_tx()

    def create_table(self, data: model.Layer0Creation, tx: psycopg.Transaction | None = None) -> int:
        """
        Creates table, writes metadata and returns integer that identifies the table for
        further requests.
        """
        # TODO: use tx or new transaction here
        fields = []
        comment_queries = []

        for column_descr in data.column_descriptions:
            fields.append((column_descr.name, column_descr.data_type))
            col_params = {
                "description": column_descr.description,
                "unit": column_descr.unit,
                "data_type": column_descr.data_type,
            }
            if column_descr.coordinate_part is not None:
                col_params["coordinate_part"] = {
                    "descr_id": column_descr.coordinate_part.descr_id,
                    "arg_num": column_descr.coordinate_part.arg_num,
                    "column_name": column_descr.coordinate_part.column_name,
                }
            if column_descr.ucd is not None:
                col_params["ucd"] = column_descr.ucd
            comment_queries.append(
                template.render_query(
                    template.ADD_COLUMN_COMMENT,
                    schema=RAWDATA_SCHEMA,
                    table_name=data.table_name,
                    column_name=column_descr.name,
                    params=json.dumps(col_params),
                )
            )

        row = self._storage.query_one(
            template.INSERT_TABLE_REGISTRY_ITEM,
            params=[data.bibliography_id, data.table_name, data.datatype],
            tx=tx,
        )
        table_id = int(row.get("id"))

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
                    params=json.dumps({"description": data.comment, "name_col": data.name_col}),
                ),
                tx=tx,
            )

        for query in comment_queries:
            self._storage.exec(query, tx=tx)

        return table_id

    def insert_raw_data(
        self,
        data: model.Layer0RawData,
        tx: psycopg.Transaction | None = None,
    ) -> None:
        """
        This method puts everything in parameters for prepared statement. This should not be a big
        issue but one would be better off using this function in batches since prepared statement make
        this quite cheap (excluding network slow down, though).
        """

        if len(data.data) == 0:
            self._logger.warn("trying to insert 0 rows into the table", table_id=data.table_id)
            return

        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[data.table_id], tx=tx)
        table_name = row.get("table_name")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {data.table_id}")

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
                table=table_name,
                fields=fields,
                objects=objects,
            ),
            params=params,
            tx=tx,
        )

    def fetch_raw_data(
        self, table_id: int, row_ids: list[str] | None = None, tx: psycopg.Transaction | None = None
    ) -> model.Layer0RawData:
        """
        :param table_id: Id of the raw table
        :param row_ids: If provided, select only given rows
        :param tx: Transaction
        :return: Layer0RawData
        """
        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[table_id], tx=tx)
        table_name = row.get("table_name")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {table_id}")

        query = template.render_query(template.FETCH_RAWDATA, schema=RAWDATA_SCHEMA, table=table_name, rows=row_ids)

        rows = self._storage.query(query)
        return model.Layer0RawData(table_id, DataFrame(rows))

    def fetch_metadata(self, table_id: int, tx: psycopg.Transaction | None = None) -> Layer0Creation:
        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[table_id], tx=tx)
        table_name = row.get("table_name")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {table_id}")

        rows = self._storage.query(template.GET_COLUMN_NAMES, params=[RAWDATA_SCHEMA, table_name])
        column_names = [it["column_name"] for it in rows]

        descriptions = []
        for column_name in column_names:
            param = self._storage.query_one(
                template.FETCH_COLUMN_METADATA, params=[RAWDATA_SCHEMA, table_name, column_name], tx=tx
            )

            if param is None:
                raise DatabaseError(f"unable to metadata for table {table_name}, column {column_name}")

            coordinate_part = None
            if param["param"].get("coordinate_part") is not None:
                coordinate_part = CoordinatePart(
                    param["param"]["coordinate_part"]["descr_id"],
                    param["param"]["coordinate_part"]["arg_num"],
                    param["param"]["coordinate_part"]["column_name"],
                )

            descriptions.append(
                ColumnDescription(
                    column_name,
                    param["param"]["data_type"],
                    param["param"]["unit"],
                    param["param"]["description"],
                    param["param"].get("ucd"),
                    coordinate_part,
                )
            )

        param = self._storage.query_one(template.FETCH_TABLE_METADATA, params=[RAWDATA_SCHEMA, table_name], tx=tx)
        registry_item = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name], tx=tx)

        if param is None:
            raise DatabaseError(f"unable to metadata for table {table_name}")

        return Layer0Creation(
            table_name,
            descriptions,
            registry_item["bib"],
            registry_item["datatype"],
            param["param"].get("name_col"),
            param["param"].get("description"),
        )

    def table_exists(self, schema: str, table_name: str) -> bool:
        try:
            self._storage.exec(f"SELECT 1 FROM {schema}.{table_name}")
        except psycopg.errors.UndefinedTable:
            return False

        return True

    def get_all_table_ids(self) -> list[int]:
        res = self._storage.query("SELECT id FROM rawdata.tables")
        return [it["id"] for it in res]
