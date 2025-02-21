import json

import structlog

from app.data import model, template
from app.data.repositories.layer0 import tables
from app.data.repositories.layer0.common import RAWDATA_SCHEMA
from app.lib.storage import enums, postgres
from app.lib.web.errors import DatabaseError


class Layer0Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

        self.table_repo = tables.Layer0TableRepository(storage)

    def create_table(self, data: model.Layer0TableMeta) -> model.Layer0CreationResponse:
        return self.table_repo.create_table(data)

    def insert_raw_data(self, data: model.Layer0RawData) -> None:
        return self.table_repo.insert_raw_data(data)

    def fetch_raw_data(
        self,
        table_id: int,
        columns: list[str] | None = None,
        order_column: str | None = None,
        order_direction: str = "asc",
        offset: int = 0,
        limit: int | None = None,
    ) -> model.Layer0RawData:
        return self.table_repo.fetch_raw_data(table_id, columns, order_column, order_direction, offset, limit)

    def fetch_metadata(self, table_id: int) -> model.Layer0TableMeta:
        return self.table_repo.fetch_metadata(table_id)

    def update_column_metadata(self, table_id: int, column_description: model.ColumnDescription) -> None:
        return self.table_repo.update_column_metadata(table_id, column_description)

    def upsert_objects(
        self,
        table_id: int,
        objects: list[model.Layer0Object],
    ) -> None:
        query = "INSERT INTO rawdata.objects (id, table_id, data) VALUES "
        params = []
        values = []

        for obj in objects:
            values.append("(%s, %s, %s)")
            params.extend([obj.object_id, table_id, json.dumps(obj.data, cls=model.CatalogObjectEncoder)])

        query += ",".join(values)
        query += " ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data, table_id = EXCLUDED.table_id"

        self._storage.exec(query, params=params)

    def upsert_old_object(
        self,
        table_id: int,
        processing_info: model.Layer0OldObject,
    ) -> None:
        self._storage.exec(
            """
            INSERT INTO rawdata.old_objects (table_id, object_id, status, data, metadata)
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

    def get_table_statistics(self, table_id: int) -> model.TableStatistics:
        statuses_query = """
            SELECT COALESCE(status, 'unprocessed') AS status, COUNT(1) 
            FROM rawdata.processing AS p
            RIGHT JOIN rawdata.objects AS o ON p.object_id = o.id
            WHERE o.table_id = %s
            GROUP BY status"""

        stats_query = """
            SELECT MAX(modification_dt) AS modification_dt , COUNT(1) AS cnt
            FROM rawdata.objects 
            WHERE table_id = %s"""

        status_rows = self._storage.query(statuses_query, params=[table_id])
        stats = self._storage.query_one(stats_query, params=[table_id])

        table_name = self._storage.query_one(template.GET_RAWDATA_TABLE, params=[table_id]).get("table_name")
        if table_name is None:
            raise DatabaseError(f"unable to fetch table with id {table_id}")

        total_original_rows_query = f'SELECT COUNT(1) AS cnt FROM {RAWDATA_SCHEMA}."{table_name}"'

        total_original_rows = self._storage.query_one(total_original_rows_query).get("cnt")
        if total_original_rows is None:
            raise DatabaseError(f"unable to fetch total rows for table {table_name}")

        return model.TableStatistics(
            {enums.ObjectProcessingStatus(row["status"]): row["count"] for row in status_rows},
            stats["modification_dt"],
            stats["cnt"],
            total_original_rows,
        )

    def get_old_object_statuses(self, table_id: int) -> dict[enums.ObjectProcessingStatus, int]:
        rows = self._storage.query(
            """
            SELECT status, COUNT(*) FROM rawdata.old_objects 
            WHERE table_id = %s 
            GROUP BY status
            """,
            params=[table_id],
        )

        return {enums.ObjectProcessingStatus(row["status"]): row["count"] for row in rows}

    def get_objects(self, table_id: int, limit: int, offset: int) -> list[model.Layer0Object]:
        rows = self._storage.query(
            """
            SELECT id, data
            FROM rawdata.objects
            WHERE table_id = %s
            LIMIT %s OFFSET %s
            """,
            params=[table_id, limit, offset],
        )

        return [
            model.Layer0Object(
                row["id"],
                json.loads(json.dumps(row["data"]), cls=model.CatalogObjectDecoder),
            )
            for row in rows
        ]

    def get_old_objects(self, table_id: int, batch_size: int, offset: int) -> list[model.Layer0OldObject]:
        rows = self._storage.query(
            """
            SELECT object_id, pgc, status, data, metadata
            FROM rawdata.old_objects
            WHERE table_id = %s
            LIMIT %s OFFSET %s
            """,
            params=[table_id, batch_size, offset],
        )

        return [
            model.Layer0OldObject(
                row["object_id"],
                enums.ObjectProcessingStatus(row["status"]),
                row["metadata"],
                json.loads(json.dumps(row["data"]), cls=model.CatalogObjectDecoder),
                row["pgc"],
            )
            for row in rows
        ]
