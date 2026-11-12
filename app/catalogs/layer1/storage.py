from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg import rows as psycopg_rows
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


_STAGE_TABLE = "_layer1_stage"
_ORDINAL_COLUMN = "_ord"


def _upsert_via_copy(
    conn: psycopg.Connection,
    table: str,
    all_columns: Sequence[str],
    conflict_keys: Sequence[str],
    rows: Sequence[Sequence[Any]],
) -> list[tuple[int, int | None]]:
    schema, relation = table.split(".", maxsplit=1)
    target = sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(relation))
    stage = sql.Identifier(_STAGE_TABLE)
    ordinal = sql.Identifier(_ORDINAL_COLUMN)
    column_idents = sql.SQL(", ").join(sql.Identifier(c) for c in all_columns)
    key_idents = sql.SQL(", ").join(sql.Identifier(c) for c in conflict_keys)
    missing_keys = [k for k in conflict_keys if k not in all_columns]
    insert_columns = [*all_columns, *missing_keys]
    insert_idents = sql.SQL(", ").join(sql.Identifier(c) for c in insert_columns)
    update_columns = [c for c in all_columns if c not in conflict_keys]
    if update_columns:
        set_clause = sql.SQL(", ").join(
            sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c)) for c in update_columns
        )
        conflict_action = sql.SQL("ON CONFLICT ({}) DO UPDATE SET {}").format(key_idents, set_clause)
    else:
        conflict_action = sql.SQL("ON CONFLICT ({}) DO NOTHING").format(key_idents)

    with conn.cursor(row_factory=psycopg_rows.tuple_row) as cur:
        if missing_keys:
            # Keys the caller did not pass must receive their column defaults before deduplication.
            cur.execute(
                sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS) ON COMMIT DROP").format(stage, target)
            )
        else:
            cur.execute(
                sql.SQL("CREATE TEMP TABLE {} ON COMMIT DROP AS SELECT {} FROM {} WITH NO DATA").format(
                    stage, column_idents, target
                )
            )
        cur.execute(sql.SQL("ALTER TABLE {} ADD COLUMN {} bigint").format(stage, ordinal))
        with cur.copy(sql.SQL("COPY {} ({}, {}) FROM STDIN").format(stage, column_idents, ordinal)) as copy:
            for i, row in enumerate(rows):
                copy.write_row([*row, i])
        # Without statistics the planner may pick a sequential scan of layer0.records for the joins below.
        cur.execute(sql.SQL("ANALYZE {}").format(stage))
        cur.execute(
            sql.SQL(
                "INSERT INTO {target} ({insert_columns}) "
                "SELECT DISTINCT ON ({keys}) {insert_columns} FROM {stage} ORDER BY {keys}, {ordinal} DESC "
                "{conflict_action}"
            ).format(
                target=target,
                insert_columns=insert_idents,
                keys=key_idents,
                stage=stage,
                ordinal=ordinal,
                conflict_action=conflict_action,
            )
        )
        cur.execute(
            sql.SQL(
                "SELECT DISTINCT r.table_id, r.pgc FROM {} AS s JOIN layer0.records AS r ON r.id = s.record_id"
            ).format(stage)
        )
        touched = cur.fetchall()
        cur.execute(sql.SQL("DROP TABLE {}").format(stage))
    return touched


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
    rows = [[rid, *vals] for rid, vals in zip(ids, data, strict=True)]
    if not rows:
        return
    touched = _upsert_via_copy(storage.get_connection(), table, all_columns, resolved_keys, rows)
    layer0.touch_tables(storage, sorted({table_id for table_id, _ in touched}))
    layer0.touch_pgcs(storage, sorted({pgc for _, pgc in touched if pgc is not None}))
