import datetime
from collections.abc import Callable

from app.data import model, repositories
from app.presentation import adminapi


def table_progress_to_presentation(progress: model.TableProgress) -> adminapi.TableProgress:
    return adminapi.TableProgress(
        total_records=progress.total_records,
        unprocessed=progress.unprocessed,
        pending_triage=progress.pending_triage,
        resolved_unsubmitted=progress.resolved_unsubmitted,
        submitted=progress.submitted,
        catalogs={
            name: adminapi.CatalogProgress(
                structured=catalog.structured,
                in_layer2=catalog.in_layer2,
                layer2_pending=catalog.layer2_pending,
            )
            for name, catalog in progress.catalogs.items()
        },
    )


def make_table_stats_refresh(
    layer0_repo: repositories.Layer0Repository,
) -> Callable[[], adminapi.TableStatsSnapshot]:
    def refresh() -> adminapi.TableStatsSnapshot:
        progress = layer0_repo.get_table_progress(None)
        return adminapi.TableStatsSnapshot(
            tables={name: table_progress_to_presentation(p) for name, p in progress.items()},
            computed_at=datetime.datetime.now(tz=datetime.UTC),
        )

    return refresh
