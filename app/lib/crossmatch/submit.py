from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from psycopg import sql

from app.lib.crossmatch.parameters import PARAMETER_ORDER
from app.lib.storage import postgres, sql_row_filter

_PARAMETER_NAMES = frozenset(parameter.value for parameter in PARAMETER_ORDER)

META = sql.SQL("meta.j")

MULTI_CANDIDATE = sql.SQL(
    """
    COALESCE(
        jsonb_typeof({meta} -> 'candidates') = 'array'
        AND jsonb_array_length({meta} -> 'candidates') > 1,
        false
    )
    """
).format(meta=META)

ELIGIBLE_ROW = sql.SQL("r.pgc IS NULL")

ELIGIBLE_META = sql.SQL("NOT ({meta} ? 'possible_matches') AND NOT ({multi})").format(meta=META, multi=MULTI_CANDIDATE)

ELIGIBLE = sql.SQL("{row} AND {meta}").format(row=ELIGIBLE_ROW, meta=ELIGIBLE_META)

IS_NEW = sql.SQL("{meta} = '{{}}'::jsonb").format(meta=META)

IS_EXISTING = sql.SQL(
    """
    (
        jsonb_typeof({meta} -> 'candidates') = 'array'
        AND jsonb_array_length({meta} -> 'candidates') = 1
    )
    OR {meta} ? 'pgc'
    """
).format(meta=META)

CANDIDATE_PGC = sql.SQL(
    """
    CASE
        WHEN jsonb_typeof({meta} -> 'candidates') = 'array'
             AND jsonb_array_length({meta} -> 'candidates') = 1
            THEN ({meta} -> 'candidates' -> 0 ->> 'pgc')::int
        ELSE ({meta} ->> 'pgc')::int
    END
    """
).format(meta=META)

CANDIDATE_PARAMETERS = sql.SQL(
    """
    CASE
        WHEN jsonb_typeof({meta} -> 'candidates') = 'array'
             AND jsonb_array_length({meta} -> 'candidates') = 1
            THEN {meta} -> 'candidates' -> 0 -> 'parameters'
        ELSE NULL
    END
    """
).format(meta=META)

OUTCOME = sql.SQL(
    """
    CASE
        WHEN {is_new} THEN 'new'
        WHEN {is_existing} THEN 'existing'
        ELSE 'unchanged'
    END
    """
).format(is_new=IS_NEW, is_existing=IS_EXISTING)

_META_LATERAL = sql.SQL("CROSS JOIN LATERAL (SELECT c.metadata::jsonb AS j) meta")

_FROM_CROSSMATCH = sql.SQL(
    """
    FROM layer0.records r
    JOIN layer0.crossmatch c ON c.record_id = r.id
    {meta}
    """
).format(meta=_META_LATERAL)


class AssignRecordPgcsPreconditionError(Exception):
    def __init__(self, sample: list[str], count: int) -> None:
        self.sample = sample
        self.count = count


@dataclass(frozen=True)
class SubmitSelection:
    table_name: str
    include_new: bool = True
    include_existing: bool = True
    require_parameters: tuple[str, ...] = ()
    row_filter: sql.Composable | None = None


def selection_from(
    *,
    table_name: str,
    include_new: bool,
    include_existing: bool,
    require_parameters: Sequence[str],
    row_filter: str | None,
) -> SubmitSelection:
    return SubmitSelection(
        table_name=table_name,
        include_new=include_new,
        include_existing=include_existing,
        require_parameters=tuple(require_parameters) if include_existing else (),
        row_filter=sql_row_filter.row_filter_clause(row_filter),
    )


def sample_query(selection: SubmitSelection) -> sql.Composed:
    frm, predicate = _filtered(selection)
    return sql.SQL(
        """
        SELECT r.id::text AS record_id,
               CASE WHEN {is_existing} THEN {pgc} END AS pgc,
               {outcome} AS outcome,
               CASE WHEN {is_existing} THEN {parameters} END AS parameters
        {frm}
        WHERE r.table_id = %s AND {predicate}
        ORDER BY r.id
        LIMIT %s
        """
    ).format(
        is_existing=IS_EXISTING,
        pgc=CANDIDATE_PGC,
        outcome=OUTCOME,
        parameters=CANDIDATE_PARAMETERS,
        frm=frm,
        predicate=predicate,
    )


def estimate_eligible_rate_query(selection: SubmitSelection) -> sql.Composed:
    passes = _passes_expression(selection)
    if selection.row_filter is None:
        return sql.SQL(
            """
            WITH s AS MATERIALIZED (
                SELECT COALESCE(({passes}), false) AS passes
                FROM layer0.records r TABLESAMPLE SYSTEM (%s)
                LEFT JOIN layer0.crossmatch c ON c.record_id = r.id
                CROSS JOIN LATERAL (SELECT c.metadata::jsonb AS j) meta
                WHERE r.table_id = %s
            )
            SELECT
                (SELECT COUNT(*)::int FROM s) AS scanned,
                (SELECT COUNT(*)::int FROM s WHERE passes) AS passing
            """
        ).format(passes=passes)
    return sql.SQL(
        """
        WITH s AS MATERIALIZED (
            SELECT COALESCE(({passes}), false) AS passes
            FROM {raw} raw TABLESAMPLE SYSTEM (%s)
            JOIN layer0.records r ON r.id = raw.{id_col}
            LEFT JOIN layer0.crossmatch c ON c.record_id = r.id
            CROSS JOIN LATERAL (SELECT c.metadata::jsonb AS j) meta
            WHERE r.table_id = %s AND ({row_filter})
        )
        SELECT
            (SELECT COUNT(*)::int FROM s) AS scanned,
            (SELECT COUNT(*)::int FROM s WHERE passes) AS passing
        """
    ).format(
        passes=passes,
        raw=sql.SQL("{}.{}").format(sql.Identifier("rawdata"), sql.Identifier(selection.table_name)),
        id_col=sql.Identifier("hyperleda_internal_id"),
        row_filter=selection.row_filter,
    )


def create_plan_query(selection: SubmitSelection) -> sql.Composed:
    row_parts: list[sql.Composable] = [ELIGIBLE_ROW]
    raw_join: sql.Composable = sql.SQL("")
    if selection.row_filter is not None:
        row_parts.append(selection.row_filter)
        raw_join = sql.SQL("JOIN {raw} raw ON raw.{id_col} = r.id").format(
            raw=sql.SQL("{}.{}").format(sql.Identifier("rawdata"), sql.Identifier(selection.table_name)),
            id_col=sql.Identifier("hyperleda_internal_id"),
        )
    meta_parts: list[sql.Composable] = [ELIGIBLE_META]
    outcome = _outcome_predicate(selection)
    if outcome is not None:
        meta_parts.append(outcome)
    # OFFSET 0 keeps the subquery from being flattened so metadata is parsed into jsonb once per row
    # instead of once per predicate.
    return sql.SQL(
        """
        CREATE TEMP TABLE submit_plan AS
        SELECT
            row_number() OVER (ORDER BY meta.rid) AS n,
            meta.rid,
            meta.record_id,
            CASE WHEN {is_new} THEN NULL ELSE {pgc} END AS pgc
        FROM (
            SELECT r.ctid AS rid, r.id AS record_id, c.metadata::jsonb AS j
            FROM layer0.records r
            JOIN layer0.crossmatch c ON c.record_id = r.id
            {raw_join}
            WHERE r.table_id = %s AND {row_predicate}
            OFFSET 0
        ) meta
        WHERE {meta_predicate}
        ORDER BY meta.rid
        """
    ).format(
        is_new=IS_NEW,
        pgc=CANDIDATE_PGC,
        raw_join=raw_join,
        row_predicate=sql.SQL(" AND ").join(row_parts),
        meta_predicate=sql.SQL(" AND ").join(meta_parts),
    )


SUBMIT_PLAN_BATCH = sql.SQL(
    """
    WITH batch AS (
        SELECT
            r.ctid AS rid,
            p.pgc IS NULL AS is_new,
            COALESCE(p.pgc, nextval(pg_get_serial_sequence('common.pgc', 'id'))::int) AS pgc
        FROM submit_plan p
        JOIN layer0.records r ON r.ctid = p.rid
        WHERE p.n > %s AND p.n <= %s AND r.id = p.record_id AND r.pgc IS NULL
        FOR UPDATE OF r
    ),
    minted AS (
        INSERT INTO common.pgc (id) SELECT pgc FROM batch WHERE is_new
    ),
    updated AS (
        UPDATE layer0.records r
        SET pgc = b.pgc
        FROM batch b
        WHERE r.ctid = b.rid
        RETURNING r.pgc, b.is_new
    ),
    changes AS (
        INSERT INTO common.pgc_changes (pgc) SELECT DISTINCT pgc FROM updated
    )
    SELECT
        COUNT(*) FILTER (WHERE is_new)::int AS new,
        COUNT(*) FILTER (WHERE NOT is_new)::int AS existing
    FROM updated
    """
)


def _filtered(selection: SubmitSelection) -> tuple[sql.Composable, sql.Composable]:
    if selection.row_filter is None:
        frm: sql.Composable = _FROM_CROSSMATCH
    else:
        frm = sql.SQL(
            """
            FROM layer0.records r
            JOIN layer0.crossmatch c ON c.record_id = r.id
            {meta}
            JOIN {raw} raw ON raw.{id_col} = r.id
            """
        ).format(
            meta=_META_LATERAL,
            raw=sql.SQL("{}.{}").format(sql.Identifier("rawdata"), sql.Identifier(selection.table_name)),
            id_col=sql.Identifier("hyperleda_internal_id"),
        )
    parts: list[sql.Composable] = [ELIGIBLE]
    if selection.row_filter is not None:
        parts.append(selection.row_filter)
    outcome = _outcome_predicate(selection)
    if outcome is not None:
        parts.append(outcome)
    return frm, sql.SQL(" AND ").join(parts)


def _passes_expression(selection: SubmitSelection) -> sql.Composable:
    parts: list[sql.Composable] = [sql.SQL("c.record_id IS NOT NULL"), ELIGIBLE]
    outcome = _outcome_predicate(selection)
    if outcome is not None:
        parts.append(outcome)
    return sql.SQL(" AND ").join(parts)


def _outcome_predicate(selection: SubmitSelection) -> sql.Composable | None:
    required = selection.require_parameters if selection.include_existing else ()
    if selection.include_new and selection.include_existing and not required:
        return None
    branches: list[sql.Composable] = []
    if selection.include_new:
        branches.append(sql.SQL("({is_new})").format(is_new=IS_NEW))
    if selection.include_existing:
        existing: sql.Composable = IS_EXISTING
        if required:
            existing = sql.SQL("(({existing}) AND {checks})").format(
                existing=IS_EXISTING,
                checks=_parameter_checks(required),
            )
        branches.append(sql.SQL("({existing})").format(existing=existing))
    return sql.SQL("({})").format(sql.SQL(" OR ").join(branches))


def _parameter_checks(names: Sequence[str]) -> sql.Composable:
    checks: list[sql.Composable] = []
    for name in names:
        if name not in _PARAMETER_NAMES:
            raise ValueError(f"unknown crossmatch parameter: {name}")
        checks.append(
            sql.SQL("(({parameters}) ->> {key})::boolean IS TRUE").format(
                parameters=CANDIDATE_PARAMETERS,
                key=sql.Literal(name),
            )
        )
    return sql.SQL(" AND ").join(checks)


def assign_record_pgcs(storage: postgres.PgStorage, record_ids: list[str]) -> None:
    if not record_ids:
        return

    invalid_from = sql.SQL(
        """
        FROM submit_staging s
        LEFT JOIN layer0.crossmatch c ON c.record_id = s.record_id
        CROSS JOIN LATERAL (SELECT c.metadata::jsonb AS j) meta
        WHERE c.record_id IS NULL
           OR meta.j ? 'possible_matches'
           OR ({multi})
        """
    ).format(multi=MULTI_CANDIDATE)
    with storage.get_connection().cursor() as cur:
        cur.execute("CREATE TEMP TABLE submit_staging (record_id text PRIMARY KEY) ON COMMIT DROP")
        with cur.copy("COPY submit_staging (record_id) FROM STDIN") as copy:
            for record_id in record_ids:
                copy.write_row((record_id,))

    invalid_rows = storage.query(
        sql.SQL("SELECT s.record_id::text AS record_id {frm} LIMIT 101").format(frm=invalid_from)
    )
    if invalid_rows:
        count_row = storage.query_one(sql.SQL("SELECT COUNT(*)::int AS cnt {frm}").format(frm=invalid_from))
        raise AssignRecordPgcsPreconditionError(
            sample=[row["record_id"] for row in invalid_rows[:100]],
            count=int(count_row["cnt"]),
        )

    storage.exec("SET LOCAL synchronous_commit = off")
    storage.query(
        """
        SELECT r.id
        FROM submit_staging s
        JOIN layer0.crossmatch c ON c.record_id = s.record_id
        JOIN layer0.records r ON r.id = s.record_id
        FOR UPDATE OF r
        """
    )
    storage.exec(
        """
        CREATE TEMP TABLE submit_assign (
            record_id text PRIMARY KEY,
            table_id int NOT NULL,
            pgc int NOT NULL
        ) ON COMMIT DROP
        """
    )
    storage.exec(
        """
        WITH classified AS (
            SELECT
                r.id AS record_id,
                r.table_id,
                CASE
                    WHEN meta.j = '{}'::jsonb THEN NULL
                    WHEN jsonb_typeof(meta.j -> 'candidates') = 'array'
                         AND jsonb_array_length(meta.j -> 'candidates') = 1
                        THEN (meta.j -> 'candidates' -> 0 ->> 'pgc')::int
                    WHEN meta.j ? 'pgc' THEN (meta.j ->> 'pgc')::int
                    ELSE NULL
                END AS existing_pgc,
                meta.j = '{}'::jsonb AS is_new
            FROM submit_staging s
            JOIN layer0.crossmatch c ON c.record_id = s.record_id
            JOIN layer0.records r ON r.id = s.record_id
            CROSS JOIN LATERAL (SELECT c.metadata::jsonb AS j) meta
            WHERE r.pgc IS NULL
              AND (
                    meta.j = '{}'::jsonb
                    OR (
                        jsonb_typeof(meta.j -> 'candidates') = 'array'
                        AND jsonb_array_length(meta.j -> 'candidates') = 1
                    )
                    OR meta.j ? 'pgc'
              )
        ),
        new_rows AS (
            SELECT record_id, row_number() OVER (ORDER BY record_id) AS rn
            FROM classified
            WHERE is_new
        ),
        minted AS (
            INSERT INTO common.pgc (id)
            SELECT nextval(pg_get_serial_sequence('common.pgc', 'id'))
            FROM new_rows
            RETURNING id
        ),
        minted_rn AS (
            SELECT id, row_number() OVER (ORDER BY id) AS rn FROM minted
        )
        INSERT INTO submit_assign (record_id, table_id, pgc)
        SELECT c.record_id, c.table_id, COALESCE(c.existing_pgc, m.id)
        FROM classified c
        LEFT JOIN new_rows n ON n.record_id = c.record_id
        LEFT JOIN minted_rn m ON m.rn = n.rn
        """
    )

    missing = storage.query(
        """
        SELECT a.record_id::text AS record_id
        FROM submit_assign a
        WHERE NOT EXISTS (SELECT 1 FROM common.pgc p WHERE p.id = a.pgc)
        LIMIT 101
        """
    )
    if missing:
        count_row = storage.query_one(
            """
            SELECT COUNT(*)::int AS cnt
            FROM submit_assign a
            WHERE NOT EXISTS (SELECT 1 FROM common.pgc p WHERE p.id = a.pgc)
            """
        )
        raise AssignRecordPgcsPreconditionError(
            sample=[row["record_id"] for row in missing[:100]],
            count=int(count_row["cnt"]),
        )

    storage.exec("SET LOCAL session_replication_role = replica")
    storage.exec(
        """
        UPDATE layer0.records r
        SET pgc = a.pgc
        FROM submit_assign a
        WHERE r.id = a.record_id AND r.pgc IS NULL
        """
    )
    storage.exec("INSERT INTO common.pgc_changes (pgc) SELECT DISTINCT pgc FROM submit_assign")
    table_ids = [int(row["table_id"]) for row in storage.query("SELECT DISTINCT table_id FROM submit_assign")]
    if table_ids:
        storage.exec(
            "UPDATE layer0.tables SET modification_dt = now() WHERE id = ANY(%s)",
            params=[table_ids],
        )


def _preview_parameters(raw: Any) -> dict[str, bool | None]:
    source = raw if isinstance(raw, dict) else {}
    return {parameter.value: source.get(parameter.value) for parameter in PARAMETER_ORDER}


def preview_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_id": row["record_id"],
            "pgc": None if row["pgc"] is None else int(row["pgc"]),
            "outcome": row["outcome"],
            "parameters": _preview_parameters(row.get("parameters")),
        }
        for row in rows
    ]


def create_submit_plan(storage: postgres.PgStorage, table_id: int, selection: SubmitSelection) -> int:
    storage.exec("DROP TABLE IF EXISTS submit_plan")
    storage.exec("SET LOCAL work_mem = '256MB'")
    storage.exec(create_plan_query(selection), params=[table_id])
    missing_from = sql.SQL(
        """
        FROM submit_plan p
        WHERE p.pgc IS NOT NULL AND NOT EXISTS (SELECT 1 FROM common.pgc g WHERE g.id = p.pgc)
        """
    )
    missing = storage.query(sql.SQL("SELECT p.record_id::text AS record_id {frm} LIMIT 101").format(frm=missing_from))
    if missing:
        count_row = storage.query_one(sql.SQL("SELECT COUNT(*)::int AS cnt {frm}").format(frm=missing_from))
        raise AssignRecordPgcsPreconditionError(
            sample=[row["record_id"] for row in missing[:100]],
            count=int(count_row["cnt"]),
        )
    storage.exec("CREATE UNIQUE INDEX ON submit_plan (n)")
    storage.exec("ANALYZE submit_plan")
    total = int(storage.query_one("SELECT COUNT(*)::int AS cnt FROM submit_plan")["cnt"])
    if total >= PREWARM_THRESHOLD:
        _prewarm(storage)
    return total


PREWARM_THRESHOLD = 50_000

# Every updated record inserts into these indexes at a random leaf page. Reading them sequentially up front is far
# cheaper on spinning disks than one random read per record.
_PREWARM_INDEXES = (
    "layer0.objects_pkey",
    "layer0.layer0_records_id_pgc_not_null",
    "layer0.layer0_records_pgc_idx",
)


def _prewarm(storage: postgres.PgStorage) -> None:
    for index in _PREWARM_INDEXES:
        storage.query("SELECT pg_prewarm(%s::regclass)", params=[index])
    storage.query(
        """
        SELECT pg_prewarm('layer0.records'::regclass, 'buffer', 'main', MIN(b), MAX(b))
        FROM (SELECT (rid::text::point)[0]::bigint AS b FROM submit_plan) blocks
        """
    )


def submit_plan_batch(storage: postgres.PgStorage, table_id: int, start: int, stop: int) -> tuple[int, int]:
    storage.exec("SET LOCAL synchronous_commit = off")
    storage.exec("SET LOCAL session_replication_role = replica")
    row = storage.query_one(SUBMIT_PLAN_BATCH, params=[start, stop])
    new, existing = int(row["new"]), int(row["existing"])
    if new + existing:
        storage.exec("UPDATE layer0.tables SET modification_dt = now() WHERE id = %s", params=[table_id])
    return new, existing


def drop_submit_plan(storage: postgres.PgStorage) -> None:
    storage.exec("DROP TABLE IF EXISTS submit_plan")
