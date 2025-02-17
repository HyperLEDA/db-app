import json

import structlog
from astropy import units as u
from pandas import DataFrame

from app import entities
from app.data import model, template
from app.entities import ColumnDescription, Layer0Creation
from app.lib.storage import enums, postgres
from app.lib.web.errors import DatabaseError

RAWDATA_SCHEMA = "rawdata"
INTERNAL_ID_COLUMN_NAME = "hyperleda_internal_id"


class Layer0Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def create_table(self, data: entities.Layer0Creation) -> entities.Layer0CreationResponse:
        """
        Creates table, writes metadata and returns integer that identifies the table for
        further requests. If table already exists, returns its ID instead of creating a new one.
        """
        table_id, ok = self.get_table_id(data.table_name)
        if ok:
            return entities.Layer0CreationResponse(table_id, False)

        fields = []

        for column_descr in data.column_descriptions:
            constraint = ""
            if column_descr.is_primary_key:
                constraint = "PRIMARY KEY"

            fields.append((column_descr.name, column_descr.data_type, constraint))

        with self.with_tx():
            row = self._storage.query_one(
                template.INSERT_TABLE_REGISTRY_ITEM,
                params=[data.bibliography_id, data.table_name, data.datatype],
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
                )

            for column_descr in data.column_descriptions:
                self.update_column_metadata(table_id, column_descr)

        return entities.Layer0CreationResponse(table_id, True)

    def insert_raw_data(
        self,
        data: entities.Layer0RawData,
    ) -> None:
        """
        This method puts everything in parameters for prepared statement. This should not be a big
        issue but one would be better off using this function in batches since prepared statements make
        this quite cheap (excluding network slow down, though).
        """

        if len(data.data) == 0:
            self._logger.warn("trying to insert 0 rows into the table", table_id=data.table_id)
            return

        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[data.table_id])
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
        )

    def fetch_raw_data(
        self,
        table_id: int,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        offset: int = 0,
        limit: int | None = None,
    ) -> entities.Layer0RawData:
        """
        :param table_id: ID of the raw table
        :param columns: select only given columns
        :param order_column: orders result by a provided column
        :param order_direction: if `order_column` is specified, sets order direction. Either `asc` or `desc`.
        :param offset: allows to retrieve rows starting from the `offset` row
        :param limit: allows to retrieve no more than `limit` rows
        :return: Layer0RawData
        """
        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[table_id])
        table_name = row.get("table_name")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {table_id}")

        columns_str = ",".join(columns or ["*"])

        params = []
        query = f"""
        SELECT {columns_str} FROM {RAWDATA_SCHEMA}."{table_name}"\n
        """

        if order_column is not None:
            query += f"ORDER BY {order_column} {order_direction}\n"

        query += "OFFSET %s\n"
        params.append(offset)

        if limit is not None:
            query += "LIMIT %s\n"
            params.append(limit)

        rows = self._storage.query(query, params=params)
        return entities.Layer0RawData(table_id, DataFrame(rows))

    def fetch_metadata(self, table_id: int) -> Layer0Creation:
        row = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[table_id])
        table_name = row.get("table_name")

        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {table_id}")

        rows = self._storage.query(template.GET_COLUMN_NAMES, params=[RAWDATA_SCHEMA, table_name])
        column_names = [it["column_name"] for it in rows]

        descriptions = []
        for column_name in column_names:
            param = self._storage.query_one(
                template.FETCH_COLUMN_METADATA,
                params=[RAWDATA_SCHEMA, table_name, column_name],
            )

            if param is None:
                raise DatabaseError(f"unable to metadata for table {table_name}, column {column_name}")

            unit = None
            if param["param"].get("unit") is not None:
                unit = u.Unit(param["param"]["unit"])

            descriptions.append(
                ColumnDescription(
                    column_name,
                    param["param"]["data_type"],
                    unit=unit,
                    description=param["param"]["description"],
                    ucd=param["param"].get("ucd"),
                )
            )

        param = self._storage.query_one(template.FETCH_TABLE_METADATA, params=[RAWDATA_SCHEMA, table_name])
        registry_item = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])

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

    def update_column_metadata(self, table_id: int, column_description: entities.ColumnDescription) -> None:
        table_name = self._get_table_name(table_id)

        column_params = {
            "description": column_description.description,
            "data_type": column_description.data_type,
        }

        if column_description.unit is not None:
            column_params["unit"] = column_description.unit.to_string()

        if column_description.ucd is not None:
            column_params["ucd"] = column_description.ucd

        query = template.render_query(
            template.ADD_COLUMN_COMMENT,
            schema=RAWDATA_SCHEMA,
            table_name=table_name,
            column_name=column_description.name,
            params=json.dumps(column_params),
        )

        self._storage.exec(query)

    def update_modification_time(self, table_id: int) -> None:
        query = "UPDATE rawdata.tables SET modification_dt = now() WHERE id = %s"

        self._storage.exec(query, params=[table_id])

    def get_table_id(self, table_name: str) -> tuple[int, bool]:
        try:
            row = self._storage.query_one(
                f"SELECT id FROM {RAWDATA_SCHEMA}.tables WHERE table_name = %s",
                params=[table_name],
            )
        except RuntimeError:
            return 0, False

        return row["id"], True

    def _get_table_name(self, table_id: int) -> str:
        row = self._storage.query_one(
            "SELECT table_name FROM rawdata.tables WHERE id = %s",
            params=[table_id],
        )
        return row["table_name"]

    def get_all_table_ids(self) -> list[int]:
        res = self._storage.query("SELECT id FROM rawdata.tables")
        return [it["id"] for it in res]

    def upsert_object(
        self,
        table_id: int,
        processing_info: model.Layer0Object,
    ) -> None:
        self._storage.exec(
            """
            INSERT INTO rawdata.objects (table_id, object_id, status, data, metadata)
            VALUES (%s, %s, %s, %s, %s) 
            ON CONFLICT (table_id, object_id) DO 
                UPDATE SET status = EXCLUDED.status, metadata = EXCLUDED.metadata
            """,
            params=[
                table_id,
                processing_info.object_id,
                processing_info.status,
                json.dumps(processing_info.data, cls=model.CatalogObjectEncoder),
                json.dumps(processing_info.metadata),
            ],
        )

    def get_object_statuses(self, table_id: int) -> dict[enums.ObjectProcessingStatus, int]:
        rows = self._storage.query(
            """
            SELECT status, COUNT(*) FROM rawdata.objects 
            WHERE table_id = %s 
            GROUP BY status
            """,
            params=[table_id],
        )

        return {enums.ObjectProcessingStatus(row["status"]): row["count"] for row in rows}

    def get_objects(self, table_id: int, batch_size: int, offset: int) -> list[model.Layer0Object]:
        rows = self._storage.query(
            """
            SELECT object_id, pgc, status, data, metadata
            FROM rawdata.objects
            WHERE table_id = %s
            LIMIT %s OFFSET %s
            """,
            params=[table_id, batch_size, offset],
        )

        return [
            model.Layer0Object(
                row["object_id"],
                enums.ObjectProcessingStatus(row["status"]),
                row["metadata"],
                json.loads(json.dumps(row["data"]), cls=model.CatalogObjectDecoder),
                row["pgc"],
            )
            for row in rows
        ]
