import datetime
from collections.abc import Callable

from app.adminapi import repository
from app.data import model
from app.specs import adminapi as spec


def table_progress_to_presentation(progress: model.TableProgress) -> spec.TableProgress:
    return spec.TableProgress(
        total_records=progress.total_records,
        unprocessed=progress.unprocessed,
        pending_triage=progress.pending_triage,
        resolved_unsubmitted=progress.resolved_unsubmitted,
        submitted=progress.submitted,
        catalogs={
            name: spec.CatalogProgress(
                structured=catalog.structured,
                in_layer2=catalog.in_layer2,
                layer2_pending=catalog.layer2_pending,
            )
            for name, catalog in progress.catalogs.items()
        },
    )


def make_table_stats_refresh(
    repo: repository.Repository,
) -> Callable[[], spec.TableStatsSnapshot]:
    def refresh() -> spec.TableStatsSnapshot:
        progress = repo.get_table_progress(None)
        return spec.TableStatsSnapshot(
            tables={name: table_progress_to_presentation(p) for name, p in progress.items()},
            computed_at=datetime.datetime.now(tz=datetime.UTC),
        )

    return refresh
