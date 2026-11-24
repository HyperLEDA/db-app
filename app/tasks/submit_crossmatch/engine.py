import time
from collections.abc import Callable
from typing import Any

import structlog

from app.lib.crossmatch import submit as crossmatch_submit
from app.specs import adminapi as spec
from app.tasks import repository

ProgressCallback = Callable[[float, str], None]
SummaryCallback = Callable[[list[dict[str, Any]], str], None]


def run(
    repo: repository.Repository,
    params: spec.SubmitCrossmatchParams,
    on_progress: ProgressCallback,
    on_summary: SummaryCallback,
    logger: structlog.stdlib.BoundLogger,
) -> None:
    selection = crossmatch_submit.selection_from(
        table_name=params.table_name,
        include_new=params.include_new,
        include_existing=params.include_existing,
        require_parameters=params.require_parameters,
        row_filter=params.row_filter,
    )
    on_progress(0, f"Planning submission for {params.table_name}")
    submitted = 0
    new_count = 0
    existing_count = 0
    eligible = 0
    try:
        plan_started = time.perf_counter()
        with repo.submit_crossmatch_plan(selection) as (table_id, eligible):
            logger.info(
                "Planned submission",
                total=eligible,
                duration_ms=round((time.perf_counter() - plan_started) * 1000, 1),
            )
            on_progress(0, f"Submitting crossmatch for {params.table_name} ({eligible} records)")
            run_started = time.perf_counter()
            for start in range(0, eligible, params.batch_size):
                stop = min(start + params.batch_size, eligible)
                batch_started = time.perf_counter()
                batch_new, batch_existing = repo.submit_crossmatch_batch(table_id, start, stop)
                submitted += batch_new + batch_existing
                new_count += batch_new
                existing_count += batch_existing
                elapsed_s = time.perf_counter() - run_started
                eta_s = round(elapsed_s * (eligible - stop) / stop) if stop < eligible else 0
                logger.info(
                    "Processed batch",
                    records_read=stop - start,
                    new=batch_new,
                    existing=batch_existing,
                    processed=stop,
                    total=eligible,
                    duration_ms=round((time.perf_counter() - batch_started) * 1000, 1),
                    eta_s=eta_s,
                )
                on_progress(min(100.0 * stop / eligible, 99.0), f"Submitted {submitted} / {eligible} records")
    finally:
        on_summary(
            [
                {"outcome": "submitted", "count": submitted},
                {"outcome": "new", "count": new_count},
                {"outcome": "existing", "count": existing_count},
            ],
            f"Submitted {submitted}/{eligible} records",
        )
        on_progress(100, "Finished")
