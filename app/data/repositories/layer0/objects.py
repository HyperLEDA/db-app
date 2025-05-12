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

    def get_objects(self, table_id: int, limit: int, offset: int) -> list[model.Layer0Object]:
        rows = self._storage.query(
            """
            SELECT id, data
            FROM rawdata.objects
            WHERE table_id = %s
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            params=[table_id, limit, offset],
        )

        return [
            model.Layer0Object(
                row["id"],
                json.loads(json.dumps(row["data"]), cls=model.Layer0CatalogObjectDecoder),
            )
            for row in rows
        ]

    def get_processed_objects(self, table_id: int, limit: int, offset: str | None) -> list[model.Layer0ProcessedObject]:
        params = []

        where_stmnt = ["table_id = %s"]
        params.append(table_id)
        if offset is not None:
            where_stmnt.append("id > %s")
            params.append(offset)

        query = f"""SELECT o.id, o.data, c.status, c.metadata
            FROM rawdata.crossmatch AS c
            JOIN (
                SELECT id, data
                FROM rawdata.objects
                WHERE {" AND ".join(where_stmnt)}
                ORDER BY id
                LIMIT %s
            ) AS o ON o.id = c.object_id
            ORDER BY o.id"""

        params.append(limit)

        rows = self._storage.query(query, params=params)

        objects = []

        for row in rows:
            status = row["status"]
            metadata = row["metadata"]
            ci_result = None

            if status == enums.ObjectCrossmatchStatus.NEW:
                ci_result = model.CIResultObjectNew()
            elif status == enums.ObjectCrossmatchStatus.EXISTING:
                ci_result = model.CIResultObjectExisting(pgc=metadata["pgc"])
            else:
                ci_result = model.CIResultObjectCollision(possible_pgcs=metadata["possible_matches"])

            objects.append(
                model.Layer0ProcessedObject(
                    row["id"],
                    json.loads(json.dumps(row["data"]), cls=model.Layer0CatalogObjectDecoder),
                    ci_result,
                )
            )

        return objects

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

    def erase_crossmatch_results(self, table_id: int) -> None:
        """
        This function locks the table while the data is deleted.
        Be careful when deleting large tables.

        TODO: consider erasing data in chunks.
        """
        self._storage.exec(
            """
            DELETE FROM rawdata.crossmatch
            WHERE object_id IN (
                SELECT id
                FROM rawdata.objects
                WHERE table_id = %s
            )
            """,
            params=[table_id],
        )

    def add_crossmatch_result(self, data: dict[str, model.CIResult]) -> None:
        query = "INSERT INTO rawdata.crossmatch (object_id, status, metadata) VALUES "
        params = []
        values = []

        for object_id, result in data.items():
            values.append("(%s, %s, %s)")

            status = None
            meta = {}

            if isinstance(result, model.CIResultObjectNew):
                status = enums.ObjectCrossmatchStatus.NEW
                meta = {}
            elif isinstance(result, model.CIResultObjectExisting):
                status = enums.ObjectCrossmatchStatus.EXISTING
                meta = {"pgc": result.pgc}
            else:
                status = enums.ObjectCrossmatchStatus.COLLIDED
                possible_pgcs = {}
                for catalog, vals in result.possible_pgcs.items():
                    possible_pgcs[catalog] = list(vals)

                meta = {"possible_matches": possible_pgcs}

            params.extend([object_id, status, json.dumps(meta)])

        query += ",".join(values)

        self._storage.exec(query, params=params)

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        values = []
        params = []

        for object_id, pgc in pgcs.items():
            params.append(object_id)
            if pgc is None:
                values.append("(%s, DEFAULT)")
            else:
                values.append("(%s, %s)")
                params.append(pgc)

        self._storage.exec(
            f"""
            INSERT INTO rawdata.pgc (object_id, id) VALUES {",".join(values)}
            ON CONFLICT (object_id) DO UPDATE SET id = EXCLUDED.id
            """,
            params=params,
        )
