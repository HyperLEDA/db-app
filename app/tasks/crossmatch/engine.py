from collections import defaultdict
from collections.abc import Callable
from typing import Any

import structlog

from app.lib.crossmatch.matching import (
    DistributionKey,
    distribution_key,
    distribution_rows,
    group_batch,
    resolve_batch,
    results_to_rows,
)
from app.lib.crossmatch.resolver import Resolver
from app.specs import adminapi as spec
from app.tasks import repository

ProgressCallback = Callable[[float, str], None]
DistributionCallback = Callable[[list[dict[str, Any]], str], None]


def run(
    repo: repository.Repository,
    params: spec.CrossmatchParams,
    log: structlog.stdlib.BoundLogger,
    on_progress: ProgressCallback,
    on_distribution: DistributionCallback,
) -> None:
    resolver = Resolver(
        radius_deg=params.radius / 3600.0,
        pgc_column=params.pgc_column.strip() or None,
        redshift_tolerance=params.redshift_tolerance if params.redshift_tolerance > 0 else None,
    )
    table_id, total_records = repo.crossmatch_table(params.table_name)
    on_progress(0, f"Starting crossmatch for {params.table_name} ({total_records} records)")

    counts: dict[DistributionKey, int] = defaultdict(int)
    total = 0
    last_id = ""
    try:
        while True:
            rows = repo.fetch_crossmatch_neighbors(table_id, last_id, params.batch_size, resolver.search_radius_deg)
            by_record, last_id = group_batch(rows)
            if not by_record:
                break

            record_ids = list(by_record)
            record_pgc_by_id = (
                repo.fetch_claimed_pgcs(params.table_name, resolver.pgc_column, record_ids)
                if resolver.pgc_column is not None
                else {}
            )
            claimed = {pgc for pgc in record_pgc_by_id.values() if pgc is not None}
            existing_pgcs = repo.layer2_pgcs(list(claimed))
            designations = [rec["new_design"] for rec in by_record.values() if rec["new_design"] is not None]
            design_to_pgcs = repo.pgcs_by_designation(designations)
            batch = resolve_batch(
                by_record,
                record_pgc_by_id,
                existing_pgcs,
                design_to_pgcs,
                resolver,
                params.print_pending,
                log,
            )
            for item in batch:
                counts[distribution_key(item.result)] += 1
                total += 1
            if params.write and batch:
                repo.set_crossmatch_results(results_to_rows([(item.record_id, item.result) for item in batch]))
            progress = 100.0 if total_records == 0 else min(100.0, 100.0 * total / total_records)
            on_progress(min(progress, 99.0), f"Processed {total} / {total_records} records")
            table = distribution_rows(counts, total)
            if table:
                on_distribution(table, f"{total} records crossmatched")
    finally:
        on_progress(100, "Finished")
        table = distribution_rows(counts, total)
        if table:
            on_distribution(table, f"Final: {total} records")
