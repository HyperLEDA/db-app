from typing import final

from app.catalogs import table_statistics
from app.tasks import layer2_common


def _empty_progress() -> table_statistics.TableProgress:
    return table_statistics.TableProgress(
        total_records=0,
        unprocessed=0,
        pending_triage=0,
        resolved_unsubmitted=0,
        submitted=0,
        catalogs={},
        columns={},
    )


@final
class RefreshTableStatsTask(layer2_common.Layer2StorageTask):
    @classmethod
    def name(cls) -> str:
        return "refresh-table-stats"

    def run(self) -> None:
        stale = self.repository.list_tables_needing_statistics_refresh()
        for table_name, observed_dt in stale:
            progress = self.repository.get_table_progress([table_name]).get(table_name)
            if progress is None:
                progress = _empty_progress()
            progress.columns = self.repository.get_column_progress(table_name)
            self.repository.save_table_statistics(table_name, progress, observed_dt)
