from collections.abc import Callable
from typing import Any

from app.specs import adminapi as spec
from app.tasks import repository

ProgressCallback = Callable[[float, str], None]
SummaryCallback = Callable[[list[dict[str, Any]], str], None]


def run(
    repo: repository.Repository,
    params: spec.SubmitCrossmatchParams,
    on_progress: ProgressCallback,
    on_summary: SummaryCallback,
) -> None:
    table_id, eligible = repo.submit_crossmatch_table(params.table_name)
    on_progress(0, f"Submitting crossmatch for {params.table_name} ({eligible} records)")
    submitted = 0
    new_count = 0
    existing_count = 0
    last_id = ""
    try:
        while batch := repo.fetch_submit_crossmatch_batch(table_id, last_id, params.batch_size):
            record_ids = [str(row["record_id"]) for row in batch]
            last_id = record_ids[-1]
            repo.assign_record_pgcs(record_ids)
            submitted += len(record_ids)
            new_count += sum(row["outcome"] == "new" for row in batch)
            existing_count += sum(row["outcome"] == "existing" for row in batch)
            progress = 100.0 if eligible == 0 else min(100.0, 100.0 * submitted / eligible)
            on_progress(min(progress, 99.0), f"Submitted {submitted} / {eligible} records")
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
