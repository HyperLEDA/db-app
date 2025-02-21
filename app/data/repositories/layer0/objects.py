import json

from app.data import model, template
from app.data.repositories.layer0.common import RAWDATA_SCHEMA
from app.lib.storage import enums, postgres
from app.lib.web.errors import DatabaseError


class Layer0ObjectRepository(postgres.TransactionalPGRepository):
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

    def get_table_statistics(self, table_id: int) -> model.TableStatistics:
        statuses_query = """
            SELECT COALESCE(status, 'unprocessed') AS status, COUNT(1) 
            FROM rawdata.crossmatch AS p
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
            {enums.ObjectCrossmatchStatus(row["status"]): row["count"] for row in status_rows},
            stats["modification_dt"],
            stats["cnt"],
            total_original_rows,
        )

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
