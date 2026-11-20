from collections import defaultdict
from collections.abc import Callable
from typing import Any

from app.lib.crossmatch.matching import (
    DistributionKey,
    distribution_key,
    distribution_rows,
    group_inputs,
    resolve_batch,
    results_to_rows,
)
from app.lib.crossmatch.resolver import Resolver
from app.lib.storage import sql_row_filter
from app.specs import adminapi as spec
from app.tasks import repository

ProgressCallback = Callable[[float, str], None]
DistributionCallback = Callable[[list[dict[str, Any]], str], None]


def run(
    repo: repository.Repository,
    params: spec.CrossmatchParams,
    on_progress: ProgressCallback,
    on_distribution: DistributionCallback,
) -> None:
    pgc_column = params.pgc_column.strip()
    include_pgc = bool(pgc_column)
    include_redshift = params.include_redshift and params.redshift_tolerance > 0
    resolver = Resolver(
        radius_deg=params.radius_arcsec / 3600.0,
        pgc_column=pgc_column or None,
        redshift_tolerance=params.redshift_tolerance if include_redshift else None,
        include_pgc=include_pgc,
        include_redshift=include_redshift,
        include_nature=params.include_nature,
    )
    row_filter = sql_row_filter.row_filter_clause(params.row_filter)
    table_id, total_records = repo.crossmatch_table(params.table_name, row_filter)
    on_progress(0, f"Starting crossmatch for {params.table_name} ({total_records} records)")

    counts: dict[DistributionKey, int] = defaultdict(int)
    total = 0

    def emit_distribution(message: str) -> None:
        table = distribution_rows(counts, total)
        if table:
            on_distribution(table, message)

    try:
        with repo.crossmatch_source(table_id, params.table_name, row_filter, resolver.pgc_column) as source:
            while inputs := source.fetch(params.batch_size):
                located = [row for row in inputs if row["ra"] is not None and row["dec"] is not None]
                neighbors = source.neighbors(
                    [str(row["id"]) for row in located],
                    [float(row["ra"]) for row in located],
                    [float(row["dec"]) for row in located],
                    resolver.search_radius_deg,
                )
                record_pgc_by_id = (
                    {
                        str(row["id"]): int(row["claimed_pgc"]) if row["claimed_pgc"] is not None else None
                        for row in inputs
                    }
                    if resolver.pgc_column is not None
                    else {}
                )
                claimed = {pgc for pgc in record_pgc_by_id.values() if pgc is not None}
                batch = resolve_batch(
                    group_inputs(inputs, neighbors),
                    record_pgc_by_id,
                    repo.layer2_pgcs(list(claimed)),
                    {row["design"]: row["same_name_pgcs"] or [] for row in inputs if row["design"] is not None},
                    resolver,
                )
                for item in batch:
                    counts[distribution_key(item.result)] += 1
                    total += 1
                if batch:
                    repo.set_crossmatch_results(results_to_rows([(item.record_id, item.result) for item in batch]))
                progress = 100.0 if total_records == 0 else min(100.0, 100.0 * total / total_records)
                on_progress(min(progress, 99.0), f"Processed {total} / {total_records} records")
                emit_distribution(f"{total} records crossmatched")
    finally:
        on_progress(100, "Finished")
        emit_distribution(f"Final: {total} records")
