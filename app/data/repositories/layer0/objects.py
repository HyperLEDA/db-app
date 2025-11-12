import json

from app.data import model, template
from app.data.repositories.layer0.common import RAWDATA_SCHEMA
from app.lib import concurrency
from app.lib.storage import enums, postgres
from app.lib.web.errors import DatabaseError


class Layer0ObjectRepository(postgres.TransactionalPGRepository):
    def register_records(self, table_id: int, record_ids: list[str]) -> None:
        if len(record_ids) == 0:
            raise RuntimeError("no records to upsert")

        query = "INSERT INTO layer0.objects (id, table_id) VALUES "
        params = []
        values = []

        for record_id in record_ids:
            values.append("(%s, %s)")
            params.extend([record_id, table_id])

        query += ",".join(values)
        query += " ON CONFLICT (id) DO UPDATE SET table_id = EXCLUDED.table_id"

        self._storage.exec(query, params=params)

    def get_processed_records(
        self,
        limit: int,
        offset: str | None = None,
        table_name: str | None = None,
        status: enums.RecordCrossmatchStatus | None = None,
        record_id: str | None = None,
    ) -> list[model.RecordCrossmatch]:
        params = []

        where_stmnt = []
        join_tables = """
            FROM layer0.objects AS o
            JOIN rawdata.crossmatch AS c ON o.id = c.object_id
        """

        if table_name is not None:
            join_tables += " JOIN layer0.tables AS t ON o.table_id = t.id"
            where_stmnt.append("t.table_name = %s")
            params.append(table_name)

        if offset is not None:
            where_stmnt.append("o.id > %s")
            params.append(offset)

        if status is not None:
            where_stmnt.append("c.status = %s")
            params.append(status)

        if record_id is not None:
            where_stmnt.append("o.id = %s")
            params.append(record_id)

        where_clause = f"WHERE {' AND '.join(where_stmnt)}" if where_stmnt else ""

        query = f"""SELECT o.id, c.status, c.metadata
            {join_tables}
            {where_clause}
            ORDER BY o.id
            LIMIT %s"""

        params.append(limit)

        rows = self._storage.query(query, params=params)

        objects = []

        for row in rows:
            status = row["status"]
            metadata = row["metadata"]
            ci_result = None

            if status == enums.RecordCrossmatchStatus.NEW:
                ci_result = model.CIResultObjectNew()
            elif status == enums.RecordCrossmatchStatus.EXISTING:
                ci_result = model.CIResultObjectExisting(pgc=metadata["pgc"])
            else:
                ci_result = model.CIResultObjectCollision(pgcs=metadata["possible_matches"])

            objects.append(
                model.RecordCrossmatch(
                    model.Record(
                        row["id"],
                        [],
                    ),
                    ci_result,
                )
            )

        return objects

    def get_table_statistics(self, table_name: str) -> model.TableStatistics:
        table_id_row = self._storage.query_one(template.FETCH_RAWDATA_REGISTRY, params=[table_name])
        if table_id_row is None:
            raise DatabaseError(f"unable to fetch table with name {table_name}")

        table_id = table_id_row["id"]

        errgr = concurrency.ErrorGroup()
        status_rows_res = errgr.run(
            self._storage.query,
            """
            SELECT COALESCE(status, 'unprocessed') AS status, COUNT(1) 
            FROM rawdata.crossmatch AS p
            RIGHT JOIN layer0.objects AS o ON p.object_id = o.id
            WHERE o.table_id = %s
            GROUP BY status""",
            params=[table_id],
        )
        stats_res = errgr.run(
            self._storage.query_one,
            """
            SELECT COUNT(1) AS cnt, MAX(t.modification_dt) AS modification_dt
            FROM layer0.objects AS o
            JOIN layer0.tables AS t ON o.table_id = t.id
            WHERE table_id = %s""",
            params=[table_id],
        )
        total_original_rows_res = errgr.run(
            self._storage.query_one, f'SELECT COUNT(1) AS cnt FROM {RAWDATA_SCHEMA}."{table_name}"'
        )
        errgr.wait()

        status_rows = status_rows_res.result()
        stats = stats_res.result()
        total_original_rows = total_original_rows_res.result().get("cnt")

        if total_original_rows is None:
            raise DatabaseError(f"unable to fetch total rows for table {table_name}")

        return model.TableStatistics(
            {enums.RecordCrossmatchStatus(row["status"]): row["count"] for row in status_rows},
            stats["modification_dt"],
            stats["cnt"],
            total_original_rows,
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
                status = enums.RecordCrossmatchStatus.NEW
                meta = {}
            elif isinstance(result, model.CIResultObjectExisting):
                status = enums.RecordCrossmatchStatus.EXISTING
                meta = {"pgc": result.pgc}
            else:
                status = enums.RecordCrossmatchStatus.COLLIDED
                possible_pgcs = list(result.pgcs)

                meta = {"possible_matches": possible_pgcs}

            params.extend([object_id, status, json.dumps(meta)])

        query += ",".join(values)
        query += " ON CONFLICT (object_id) DO UPDATE SET status = EXCLUDED.status, metadata = EXCLUDED.metadata"

        self._storage.exec(query, params=params)

    def upsert_pgc(self, pgcs: dict[str, int | None]) -> None:
        pgcs_to_insert: dict[str, int] = {}

        new_objects = [object_id for object_id, pgc in pgcs.items() if pgc is None]

        if new_objects:
            result = self._storage.query(
                f"""INSERT INTO common.pgc 
                VALUES {",".join(["(DEFAULT)"] * len(new_objects))} 
                RETURNING id""",
            )

            ids = [row["id"] for row in result]

            for object_id, pgc_id in zip(new_objects, ids, strict=False):
                pgcs_to_insert[object_id] = pgc_id

        for object_id, pgc in pgcs.items():
            if pgc is not None:
                pgcs_to_insert[object_id] = pgc

        if pgcs_to_insert:
            update_query = "UPDATE layer0.objects SET pgc = v.pgc FROM (VALUES "
            params = []
            values = []

            for object_id, pgc_id in pgcs_to_insert.items():
                values.append("(%s, %s)")
                params.extend([object_id, pgc_id])

            update_query += ",".join(values)
            update_query += ") AS v(object_id, pgc) WHERE layer0.objects.id = v.object_id"

            self._storage.exec(update_query, params=params)
