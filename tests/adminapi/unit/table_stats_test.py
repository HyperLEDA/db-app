from unittest import mock

from app.adminapi import model
from app.adminapi.domain import table_stats


def test_table_progress_to_presentation() -> None:
    progress = model.TableProgress(
        total_records=10,
        unprocessed=1,
        pending_triage=2,
        resolved_unsubmitted=3,
        submitted=4,
        catalogs={
            "icrs": model.CatalogProgress(structured=5, in_layer2=3, layer2_pending=1),
        },
    )

    result = table_stats.table_progress_to_presentation(progress)

    assert result.total_records == 10
    assert result.catalogs["icrs"].structured == 5
    assert result.catalogs["icrs"].in_layer2 == 3
    assert result.catalogs["icrs"].layer2_pending == 1


def test_make_table_stats_refresh() -> None:
    repo = mock.MagicMock()
    repo.get_table_progress.return_value = {
        "t1": model.TableProgress(
            total_records=1,
            unprocessed=0,
            pending_triage=0,
            resolved_unsubmitted=0,
            submitted=1,
            catalogs={},
        )
    }

    refresh = table_stats.make_table_stats_refresh(repo)
    snapshot = refresh()

    assert "t1" in snapshot.tables
    assert snapshot.tables["t1"].submitted == 1
    repo.get_table_progress.assert_called_once_with(None)
