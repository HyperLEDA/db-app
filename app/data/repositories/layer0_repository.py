import json

import structlog
from astropy import units as u
from pandas import DataFrame

from app import entities
from app.data import template
from app.data.mappers import domain_to_data
from app.data.mappers.data_to_domain import layer_0_mapper
from app.data.repositories import CommonRepository
from app.domain import repositories
from app.domain.model import Layer0Model
from app.domain.model.params.layer_0_query_param import Layer0QueryParam
from app.entities import ColumnDescription, CoordinatePart, Layer0Creation
from app.lib.storage import enums, postgres
from app.lib.web.errors import DatabaseError

RAWDATA_SCHEMA = "rawdata"
INTERNAL_ID_COLUMN_NAME = "hyperleda_internal_id"


class Layer0Repository(postgres.TransactionalPGRepository, repositories.Layer0Repository):
    def __init__(
        self, common_repository: CommonRepository, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger
    ) -> None:
        self._common_repository: CommonRepository = common_repository
        self._logger = logger
        super().__init__(storage)

    def create_table(self, data: entities.Layer0Creation) -> entities.Layer0CreationResponse:
        """
        Creates table, writes metadata and returns integer that identifies the table for
        further requests. If table already exists, returns its ID instead of creating a new one.
        """
        fields = []
        comment_queries = []

        for column_descr in data.column_descriptions:
            constraint = ""
            if column_descr.is_primary_key:
                constraint = "PRIMARY KEY"

            fields.append((column_descr.name, column_descr.data_type, constraint))
            col_params = {
                "description": column_descr.description,
                "data_type": column_descr.data_type,
            }

            if column_descr.unit is not None:
                col_params["unit"] = column_descr.unit.to_string()

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

        table_id, ok = self.get_table_id(data.table_name)
        if ok:
            return entities.Layer0CreationResponse(table_id, False)

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

            for query in comment_queries:
                self._storage.exec(query)

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
        query = f"SELECT {columns_str} FROM {RAWDATA_SCHEMA}.{table_name}\n"

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

            coordinate_part = None
            if param["param"].get("coordinate_part") is not None:
                coordinate_part = CoordinatePart(
                    param["param"]["coordinate_part"]["descr_id"],
                    param["param"]["coordinate_part"]["arg_num"],
                    param["param"]["coordinate_part"]["column_name"],
                )

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
                    coordinate_part=coordinate_part,
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

    def get_table_id(self, table_name: str) -> tuple[int, bool]:
        try:
            row = self._storage.query_one(
                f"SELECT id FROM {RAWDATA_SCHEMA}.tables WHERE table_name = %s",
                params=[table_name],
            )
        except RuntimeError:
            return 0, False

        return row["id"], True

    def get_all_table_ids(self) -> list[int]:
        res = self._storage.query("SELECT id FROM rawdata.tables")
        return [it["id"] for it in res]

    def upsert_object(self, table_id: int, obj: entities.ObjectProcessingInfo) -> None:
        self._storage.exec(
            """
            INSERT INTO rawdata.objects (table_id, object_id, pgc, status, data, metadata)
            VALUES (%s, %s, %s, %s, %s, %s) 
            ON CONFLICT (table_id, object_id) DO 
                UPDATE SET status = EXCLUDED.status, metadata = EXCLUDED.metadata
            """,
            params=[
                table_id,
                obj.object_id,
                obj.pgc,
                obj.status,
                json.dumps(obj.data, cls=entities.ObjectInfoEncoder),
                json.dumps(obj.metadata),
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

    def get_objects(self, batch_size: int, offset: int) -> list[entities.ObjectProcessingInfo]:
        rows = self._storage.query(
            """
            SELECT object_id, pgc, status, data, metadata
            FROM rawdata.objects
            LIMIT %s OFFSET %s
            """,
            params=[batch_size, offset],
        )

        return [
            entities.ObjectProcessingInfo(
                row["object_id"],
                enums.ObjectProcessingStatus(row["status"]),
                row["metadata"],
                entities.ObjectInfo.load(row["data"]),
                row["pgc"],
            )
            for row in rows
        ]

    def create_update_instances(self, instances: list[Layer0Model]):
        pass

    def create_instances(self, instances: list[Layer0Model]):
        with self.with_tx():
            for instance in instances:
                bibliography = domain_to_data.layer_0_bibliography_mapper(instance)
                bibliography_id = self._common_repository.create_bibliography(
                    bibliography.code,
                    bibliography.year,
                    bibliography.author,
                    bibliography.title,
                )
                creation = domain_to_data.layer_0_creation_mapper(instance, bibliography_id)
                table_resp = self.create_table(creation)
                raw = domain_to_data.layer_0_raw_mapper(instance, table_resp.table_id)
                self.insert_raw_data(raw)

    def fetch_data(self, param: Layer0QueryParam) -> list[Layer0Model]:
        with self.with_tx():
            # TODO use some selection params to filter unneeded tables
            ids = self.get_all_table_ids()

            to_domain = []
            for table_id in ids:
                meta = self.fetch_metadata(table_id)
                raw = self.fetch_raw_data(table_id)
                bib = self._common_repository.get_source_by_id(meta.bibliography_id)
                to_domain.append(layer_0_mapper(meta, raw, bib))

        return to_domain
