import re
import unittest
from unittest import mock

from app import catalogs
from app.dataapi import repository


class QueryCatalogsJoinTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = mock.Mock()
        self.storage.query.return_value = []
        self.repo = repository.Repository(self.storage, mock.Mock())

    def _one_to_one_query_for(self, raw_catalogs: list[catalogs.RawCatalog]) -> str:
        self.repo.query_catalogs(raw_catalogs, [1, 2])
        queries = [call.args[0] for call in self.storage.query.call_args_list]
        join_queries = [q for q in queries if "unnest" in q]
        self.assertEqual(len(join_queries), 1)
        return re.sub(r"\s+", " ", join_queries[0]).strip()

    def test_one_to_one_uses_unnest_left_join(self):
        query = self._one_to_one_query_for(
            [catalogs.RawCatalog.DESIGNATION, catalogs.RawCatalog.ICRS, catalogs.RawCatalog.REDSHIFT],
        )

        self.assertIn("unnest(%s::int[]) WITH ORDINALITY", query)
        self.assertIn("LEFT JOIN layer2.designation USING (pgc)", query)
        self.assertIn("LEFT JOIN layer2.icrs USING (pgc)", query)
        self.assertIn("LEFT JOIN layer2.cz USING (pgc)", query)
        self.assertNotIn("FULL JOIN", query)
        self.assertNotIn("search_params", query)

    def test_one_to_many_catalogs_use_separate_queries(self):
        self.repo.query_catalogs(
            [catalogs.RawCatalog.PHOTOMETRY__TOTAL, catalogs.RawCatalog.NOTE],
            [1],
        )
        queries = [call.args[0] for call in self.storage.query.call_args_list]
        self.assertTrue(any("layer2.photometry_total" in q for q in queries))
        self.assertTrue(any("layer2.notes" in q for q in queries))
        self.assertFalse(any("unnest" in q for q in queries))

    def test_mixed_catalogs_join_only_one_to_one(self):
        self.repo.query_catalogs(
            [catalogs.RawCatalog.ICRS, catalogs.RawCatalog.PHOTOMETRY__TOTAL],
            [1],
        )
        queries = [call.args[0] for call in self.storage.query.call_args_list]
        join_queries = [q for q in queries if "unnest" in q]
        self.assertEqual(len(join_queries), 1)
        query = re.sub(r"\s+", " ", join_queries[0]).strip()
        self.assertIn("LEFT JOIN layer2.icrs USING (pgc)", query)
        self.assertNotIn("photometry_total", query)
        self.assertTrue(any("layer2.photometry_total" in q for q in queries))
