import unittest
from unittest import mock

from app.data import model
from app.domain.adminapi import table_stats


class TableStatsTest(unittest.TestCase):
    def test_table_progress_to_presentation(self) -> None:
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

        self.assertEqual(result.total_records, 10)
        self.assertEqual(result.catalogs["icrs"].structured, 5)
        self.assertEqual(result.catalogs["icrs"].in_layer2, 3)
        self.assertEqual(result.catalogs["icrs"].layer2_pending, 1)

    def test_make_table_stats_refresh(self) -> None:
        layer0_repo = mock.MagicMock()
        layer0_repo.get_table_progress.return_value = {
            "t1": model.TableProgress(
                total_records=1,
                unprocessed=0,
                pending_triage=0,
                resolved_unsubmitted=0,
                submitted=1,
                catalogs={},
            )
        }

        refresh = table_stats.make_table_stats_refresh(layer0_repo)
        snapshot = refresh()

        self.assertIn("t1", snapshot.tables)
        self.assertEqual(snapshot.tables["t1"].submitted, 1)
        layer0_repo.get_table_progress.assert_called_once_with(None)
