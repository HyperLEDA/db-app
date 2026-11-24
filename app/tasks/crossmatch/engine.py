import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import structlog

from app.lib.crossmatch.matching import (
    DistributionKey,
    distribution_key,
    distribution_rows,
    resolve_inputs,
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
    logger: structlog.stdlib.BoundLogger,
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
    run_started = time.perf_counter()

    def emit_distribution(message: str) -> list[dict[str, Any]]:
        table = distribution_rows(counts, total)
        if table:
            on_distribution(table, message)
        return table

    try:
        with repo.crossmatch_source(
            table_id,
            params.table_name,
            row_filter,
            resolver.pgc_column,
            resolver.search_radius_deg,
            total_records,
            include_redshift=include_redshift,
            include_nature=params.include_nature,
        ) as source:
            while inputs := source.fetch(params.batch_size):
                batch_started = time.perf_counter()
                batch = resolve_inputs(inputs, resolver, repo.layer2_pgcs)
                for item in batch:
                    counts[distribution_key(item.result)] += 1
                    total += 1
                if batch:
                    repo.set_crossmatch_results(
                        table_id, results_to_rows([(item.record_id, item.result) for item in batch])
                    )
                elapsed_s = time.perf_counter() - run_started
                eta_s = round(elapsed_s * (total_records - total) / total) if 0 < total < total_records else 0
                table = emit_distribution(f"{total} records crossmatched")
                logger.info(
                    "Processed batch",
                    records_read=len(inputs),
                    counts=[(row["status"], row["triage"], row["parameters"], row["count"]) for row in table],
                    processed=total,
                    total=total_records,
                    duration_ms=round((time.perf_counter() - batch_started) * 1000, 1),
                    eta_s=eta_s,
                )
                progress = 100.0 if total_records == 0 else min(100.0, 100.0 * total / total_records)
                on_progress(min(progress, 99.0), f"Processed {total} / {total_records} records")
    finally:
        on_progress(100, "Finished")
