from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg import sql

from app.catalogs import designation_normalization, layer0
from app.catalogs.layer1.interface import Catalog
from app.lib.storage import postgres

_INTERNAL_COLUMNS = frozenset({"record_id", "object_id", "id"})


def writable_columns(table_info: postgres.TableInfo) -> list[postgres.ColumnInfo]:
    return [col for name, col in table_info.columns.items() if name not in _INTERNAL_COLUMNS]


def normalize_catalog_rows(
    catalog: Catalog,
    columns: Sequence[str],
    rows: list[list[Any]],
) -> list[list[Any]]:
    if catalog is not Catalog.DESIGNATION or "design" not in columns:
        return rows
    design_idx = list(columns).index("design")
    for row in rows:
        row[design_idx] = designation_normalization.normalize_designation(str(row[design_idx]))
    return rows


def format_foreign_key_violation(exc: psycopg.errors.ForeignKeyViolation) -> str:
    diag = getattr(exc, "diag", None)
    detail = getattr(diag, "message_detail", None) if diag else None
    constraint = getattr(diag, "constraint_name", None) if diag else None
    msg = "foreign key violation"
    if constraint:
        msg += f": {constraint}"
    if detail:
        msg += f" ({detail})"
    return msg


def save_structured_data(
    storage: postgres.PgStorage,
    table: str,
    columns: Sequence[str],
    ids: Sequence[str],
    data: Sequence[Sequence[Any]],
    conflict_keys: Sequence[str] | None = None,
) -> None:
    resolved_keys = list(conflict_keys) if conflict_keys is not None else ["record_id"]
    all_columns = ["record_id", *columns]
    schema, relation = table.split(".", maxsplit=1)
    table_ident = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(relation))
    column_idents = sql.SQL(", ").join(sql.Identifier(c) for c in all_columns)
    placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in all_columns)
    conflict_idents = sql.SQL(", ").join(sql.Identifier(c) for c in resolved_keys)
    update_columns = [c for c in all_columns if c not in resolved_keys]
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
    rows = [[rid, *vals] for rid, vals in zip(ids, data, strict=True)]
    with layer0.rawdata_table(storage, record_ids=ids):
        storage.execute_batch(query_str, rows)
        pgc_rows = storage.query(
            "SELECT DISTINCT pgc FROM layer0.records WHERE id = ANY(%s) AND pgc IS NOT NULL",
            params=[list(ids)],
        )
        layer0.touch_pgcs(storage, [int(row["pgc"]) for row in pgc_rows])
