from collections.abc import Sequence
from typing import Any

from psycopg import sql

from app.lib.storage import postgres


def create_bibliography(
    storage: postgres.PgStorage,
    code: str,
    year: int,
    authors: list[str],
    title: str,
) -> int:
    result = storage.query_one(
        """
        INSERT INTO common.bib (code, year, author, title)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (code) DO UPDATE SET year = EXCLUDED.year, author = EXCLUDED.author, title = EXCLUDED.title
        RETURNING id
        """,
        params=[code, year, authors, title],
    )
    return int(result["id"])


def create_table(
    storage: postgres.PgStorage,
    table_name: str,
    bib_id: int,
    *,
    datatype: str = "regular",
) -> int:
    row = storage.query_one(
        """
        INSERT INTO layer0.tables (bib, table_name, datatype)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        params=[bib_id, table_name, datatype],
    )
    table_id = int(row["id"])
    storage.exec(
        sql.SQL("CREATE TABLE {}.{} ()").format(
            sql.Identifier("rawdata"),
            sql.Identifier(table_name),
        )
    )
    return table_id


def register_records(storage: postgres.PgStorage, table_name: str, record_ids: list[str]) -> None:
    table_id_row = storage.query_one(
        "SELECT * FROM layer0.tables WHERE table_name=%s",
        params=[table_name],
    )
    table_id = table_id_row["id"]
    query = (
        "INSERT INTO layer0.records (id, table_id) VALUES (%s, %s) "
        "ON CONFLICT (id) DO UPDATE SET table_id = EXCLUDED.table_id"
    )
    storage.execute_batch(query, [[record_id, table_id] for record_id in record_ids])


def register_pgcs(storage: postgres.PgStorage, pgcs: list[int]) -> None:
    storage.execute_batch(
        "INSERT INTO common.pgc (id) VALUES (%s) ON CONFLICT (id) DO NOTHING",
        [[pgc] for pgc in pgcs],
    )


def upsert_pgc(storage: postgres.PgStorage, pgcs: dict[str, int | None]) -> None:
    pgcs_to_insert: dict[str, int] = {}
    new_records = [record_id for record_id, pgc in pgcs.items() if pgc is None]
    if new_records:
        rows = storage.query(
            f"""INSERT INTO common.pgc (id)
            VALUES {",".join(["(DEFAULT)"] * len(new_records))}
            RETURNING id"""
        )
        for record_id, row in zip(new_records, rows, strict=True):
            pgcs_to_insert[record_id] = int(row["id"])
    for record_id, pgc in pgcs.items():
        if pgc is not None:
            pgcs_to_insert[record_id] = pgc
    if pgcs_to_insert:
        update_query = (
            "UPDATE layer0.records SET pgc = v.pgc FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
            "WHERE layer0.records.id = v.record_id"
        )
        storage.execute_batch(
            update_query,
            [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()],
        )
        storage.exec(
            "UPDATE common.pgc SET modification_time = NOW() WHERE id = ANY(%s)",
            params=[list(set(pgcs_to_insert.values()))],
        )


def save_structured_data(
    storage: postgres.PgStorage,
    table: str,
    columns: list[str],
    ids: list[str],
    data: list[list[Any]],
    conflict_keys: list[str] | None = None,
) -> None:
    if conflict_keys is None:
        conflict_keys = ["record_id"]
    all_columns = ["record_id"] + columns
    schema, relation = table.split(".", maxsplit=1)
    table_ident = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(relation))
    column_idents = sql.SQL(", ").join(sql.Identifier(c) for c in all_columns)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in all_columns)
    conflict_idents = sql.SQL(", ").join(sql.Identifier(c) for c in conflict_keys)
    update_columns = [c for c in all_columns if c not in conflict_keys]
    if update_columns:
        on_conflict_set = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in update_columns
        )
        conflict_action = sql.SQL("ON CONFLICT ({}) DO UPDATE SET {}").format(conflict_idents, on_conflict_set)
    else:
        conflict_action = sql.SQL("ON CONFLICT ({}) DO NOTHING").format(conflict_idents)
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) {}").format(
        table_ident, column_idents, placeholders, conflict_action
    )
    query_str = storage.query_str(query)
    rows = [[rid] + vals for rid, vals in zip(ids, data, strict=True)]
    storage.execute_batch(query_str, rows)
    pgc_rows = storage.query(
        "SELECT DISTINCT pgc FROM layer0.records WHERE id = ANY(%s) AND pgc IS NOT NULL",
        params=[ids],
    )
    pgc_ids = [int(row["pgc"]) for row in pgc_rows]
    if pgc_ids:
        storage.exec(
            "UPDATE common.pgc SET modification_time = NOW() WHERE id = ANY(%s)",
            params=[pgc_ids],
        )


def seed_layer1_table(
    storage: postgres.PgStorage,
    table_name: str,
    record_ids: Sequence[str],
    pgcs: dict[str, int],
    layer1_table: str,
    columns: list[str],
    rows: list[list[Any]],
    *,
    conflict_keys: list[str] | None = None,
    bib_code: str = "123456",
) -> None:
    bib_id = create_bibliography(storage, bib_code, 2000, ["test"], "test")
    create_table(storage, table_name, bib_id)
    register_records(storage, table_name, list(record_ids))
    register_pgcs(storage, list(pgcs.values()))
    upsert_pgc(storage, pgcs)
    save_structured_data(storage, layer1_table, columns, list(record_ids), rows, conflict_keys=conflict_keys)
