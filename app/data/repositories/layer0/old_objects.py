import json

from app.data import model
from app.lib.storage import enums, postgres


class Layer0OldObjectsRepository(postgres.TransactionalPGRepository):
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
