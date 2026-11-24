from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from psycopg import sql

from app.lib.crossmatch.parameters import PARAMETER_ORDER
from app.lib.storage import postgres, sql_row_filter

_PARAMETER_NAMES = frozenset(parameter.value for parameter in PARAMETER_ORDER)

MULTI_CANDIDATE = sql.SQL(
    """
    COALESCE(
        jsonb_typeof(c.metadata::jsonb -> 'candidates') = 'array'
        AND jsonb_array_length(c.metadata::jsonb -> 'candidates') > 1,
        false
    )
    """
)

ELIGIBLE = sql.SQL(
    """
    r.pgc IS NULL
    AND c.triage_status = 'resolved'
    AND NOT (c.metadata::jsonb ? 'possible_matches')
    AND NOT ({multi})
    """
).format(multi=MULTI_CANDIDATE)

IS_NEW = sql.SQL("c.metadata::jsonb = '{}'::jsonb")

IS_EXISTING = sql.SQL(
    """
    (
        jsonb_typeof(c.metadata::jsonb -> 'candidates') = 'array'
        AND jsonb_array_length(c.metadata::jsonb -> 'candidates') = 1
    )
    OR c.metadata::jsonb ? 'pgc'
    """
)

CANDIDATE_PGC = sql.SQL(
    """
    CASE
        WHEN jsonb_typeof(c.metadata::jsonb -> 'candidates') = 'array'
             AND jsonb_array_length(c.metadata::jsonb -> 'candidates') = 1
            THEN (c.metadata::jsonb -> 'candidates' -> 0 ->> 'pgc')::int
        ELSE (c.metadata->>'pgc')::int
    END
    """
)

CANDIDATE_PARAMETERS = sql.SQL(
    """
    CASE
        WHEN jsonb_typeof(c.metadata::jsonb -> 'candidates') = 'array'
             AND jsonb_array_length(c.metadata::jsonb -> 'candidates') = 1
            THEN c.metadata::jsonb -> 'candidates' -> 0 -> 'parameters'
        ELSE NULL
    END
    """
)

OUTCOME = sql.SQL(
    """
    CASE
        WHEN {is_new} THEN 'new'
        WHEN {is_existing} THEN 'existing'
        ELSE 'unchanged'
    END
    """
).format(is_new=IS_NEW, is_existing=IS_EXISTING)

_FROM_CROSSMATCH = sql.SQL(
    """
    FROM layer0.records r
    JOIN layer0.crossmatch c ON c.record_id = r.id
    """
)


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


def eligible_count_query(selection: SubmitSelection) -> sql.Composed:
    frm, predicate = _filtered(selection)
    return sql.SQL(
        """
        SELECT COUNT(*)::int AS cnt
        {frm}
        WHERE r.table_id = %s AND {predicate}
        """
    ).format(frm=frm, predicate=predicate)


def page_query(selection: SubmitSelection) -> sql.Composed:
    frm, predicate = _filtered(selection)
    return sql.SQL(
        """
        SELECT r.id::text AS record_id, {outcome} AS outcome
        {frm}
        WHERE r.table_id = %s AND r.id > %s AND {predicate}
        ORDER BY r.id ASC
        LIMIT %s
        """
    ).format(outcome=OUTCOME, frm=frm, predicate=predicate)


def _filtered(selection: SubmitSelection) -> tuple[sql.Composable, sql.Composable]:
    if selection.row_filter is None:
        frm: sql.Composable = _FROM_CROSSMATCH
    else:
        frm = sql.SQL(
            """
            FROM layer0.records r
            JOIN layer0.crossmatch c ON c.record_id = r.id
            JOIN {raw} raw ON raw.{id_col} = r.id
            """
        ).format(
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
        WHERE c.record_id IS NULL
           OR c.triage_status != 'resolved'
           OR c.metadata::jsonb ? 'possible_matches'
           OR ({multi})
        """
    ).format(multi=MULTI_CANDIDATE)
    join_submit = sql.SQL(
        """
        FROM submit_staging s
        JOIN layer0.crossmatch c ON c.record_id = s.record_id
        JOIN layer0.records r ON r.id = s.record_id
        """
    )
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

    storage.query(sql.SQL("SELECT s.record_id {join} FOR UPDATE OF c, r").format(join=join_submit))
    existing_rows = storage.query(
        sql.SQL(
            """
            SELECT s.record_id::text AS record_id, {pgc} AS pgc
            {join}
            WHERE r.pgc IS NULL AND ({existing})
            ORDER BY s.record_id
            """
        ).format(pgc=CANDIDATE_PGC, join=join_submit, existing=IS_EXISTING)
    )
    new_rows = storage.query(
        sql.SQL(
            """
            SELECT s.record_id::text AS record_id
            {join}
            WHERE {is_new} AND r.pgc IS NULL
            ORDER BY s.record_id
            """
        ).format(join=join_submit, is_new=IS_NEW)
    )

    pgcs_to_insert = {row["record_id"]: int(row["pgc"]) for row in existing_rows}
    if new_rows:
        for row, pgc_id in zip(new_rows, _mint_pgc_ids(storage, len(new_rows)), strict=True):
            pgcs_to_insert[row["record_id"]] = pgc_id
    if pgcs_to_insert:
        record_ids_to_update = list(pgcs_to_insert.keys())
        table_ids = [
            int(row["table_id"])
            for row in storage.query(
                "SELECT DISTINCT table_id FROM layer0.records WHERE id = ANY(%s)",
                params=[record_ids_to_update],
            )
        ]
        storage.execute_batch(
            "UPDATE layer0.records SET pgc = v.pgc "
            "FROM (VALUES (%s, %s)) AS v(record_id, pgc) "
            "WHERE layer0.records.id = v.record_id AND layer0.records.pgc IS NULL",
            [[record_id, pgc_id] for record_id, pgc_id in pgcs_to_insert.items()],
        )
        storage.exec(
            "INSERT INTO common.pgc_changes (pgc) SELECT unnest(%s::int[])",
            params=[sorted(set(pgcs_to_insert.values()))],
        )
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


def _mint_pgc_ids(storage: postgres.PgStorage, count: int) -> list[int]:
    rows = storage.query(
        f"""INSERT INTO common.pgc (id)
        VALUES {",".join(["(DEFAULT)"] * count)}
        RETURNING id"""
    )
    return [int(row["id"]) for row in rows]
