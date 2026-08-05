import re
import unittest
from unittest import mock

from astropy import units as u

from app.data import model
from app.data.repositories import layer2
from app.data.repositories.layer2.filters import pgc_prefix_ranges


class QueryCatalogsJoinTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = mock.Mock()
        self.storage.query.return_value = []
        self.repo = layer2.Layer2Repository(self.storage, mock.Mock())

    def _query_for(
        self,
        catalogs: list[model.RawCatalog],
        search_filter: layer2.Filter,
        search_params: layer2.SearchParams,
    ) -> str:
        self.repo.query_catalogs(catalogs, search_filter, search_params, 25, 0)
        query = self.storage.query.call_args.args[0]
        return re.sub(r"\s+", " ", query).strip()

    def test_designation_filter_drives_join(self):
        query = self._query_for(
            [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS, model.RawCatalog.REDSHIFT],
            layer2.DesignationLikeFilter(),
            layer2.CombinedSearchParams([layer2.DesignationSearchParams("IC 1440")]),
        )

        self.assertNotIn("FULL JOIN", query)
        self.assertIn(
            "CROSS JOIN layer2.designation LEFT JOIN layer2.icrs USING (pgc) LEFT JOIN layer2.cz USING (pgc)",
            query,
        )

    def test_coordinate_filter_drives_join(self):
        query = self._query_for(
            [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS, model.RawCatalog.REDSHIFT],
            layer2.ICRSCoordinatesInRadiusFilter(1 * u.Unit("arcmin")),
            layer2.CombinedSearchParams(
                [layer2.ICRSSearchParams(10 * u.Unit("deg"), 10 * u.Unit("deg"))],
            ),
        )

        self.assertNotIn("FULL JOIN", query)
        self.assertIn(
            "CROSS JOIN layer2.icrs LEFT JOIN layer2.designation USING (pgc) LEFT JOIN layer2.cz USING (pgc)",
            query,
        )

    def test_pgc_filter_keeps_full_join(self):
        query = self._query_for(
            [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS],
            layer2.PGCOneOfFilter([1, 2]),
            layer2.CombinedSearchParams([layer2.DesignationSearchParams("IC 1440")]),
        )

        self.assertIn("FULL JOIN", query)
        self.assertNotIn("LEFT JOIN", query)

    def test_and_filter_drives_join_from_strict_child(self):
        query = self._query_for(
            [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS],
            layer2.AndFilter(
                [
                    layer2.PGCOneOfFilter([1, 2]),
                    layer2.ICRSCoordinatesInRadiusFilter(1 * u.Unit("arcmin")),
                ]
            ),
            layer2.CombinedSearchParams(
                [layer2.ICRSSearchParams(10 * u.Unit("deg"), 10 * u.Unit("deg"))],
            ),
        )

        self.assertNotIn("FULL JOIN", query)
        self.assertIn("CROSS JOIN layer2.icrs LEFT JOIN layer2.designation USING (pgc)", query)

    def test_or_filter_with_mixed_branches_keeps_full_join(self):
        query = self._query_for(
            [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS],
            layer2.OrFilter(
                [
                    layer2.PGCOneOfFilter([1, 2]),
                    layer2.DesignationLikeFilter(),
                ]
            ),
            layer2.CombinedSearchParams([layer2.DesignationSearchParams("IC 1440")]),
        )

        self.assertIn("FULL JOIN", query)

    def test_driving_table_is_joined_even_when_its_catalog_not_requested(self):
        query = self._query_for(
            [model.RawCatalog.REDSHIFT],
            layer2.DesignationLikeFilter(),
            layer2.CombinedSearchParams([layer2.DesignationSearchParams("IC 1440")]),
        )

        self.assertIn("CROSS JOIN layer2.designation LEFT JOIN layer2.cz USING (pgc)", query)
        self.assertNotIn('"designation|design"', query)

    def test_pgc_prefix_filter_drives_from_common_pgc(self):
        query = self._query_for(
            [model.RawCatalog.DESIGNATION, model.RawCatalog.ICRS],
            layer2.PGCPrefixFilter(12, 200000),
            layer2.CombinedSearchParams([]),
        )

        self.assertNotIn("FULL JOIN", query)
        self.assertIn(
            "CROSS JOIN (SELECT id AS pgc FROM common.pgc) AS pgc_drive "
            "LEFT JOIN layer2.designation USING (pgc) LEFT JOIN layer2.icrs USING (pgc)",
            query,
        )


class PGCPrefixRangesTest(unittest.TestCase):
    def test_ranges_for_prefix_bounded_by_max_pgc(self):
        self.assertEqual(
            pgc_prefix_ranges(12, 200000),
            [
                (12, 13),
                (120, 130),
                (1200, 1300),
                (12000, 13000),
                (120000, 130000),
            ],
        )

    def test_empty_when_prefix_beyond_max(self):
        self.assertEqual(pgc_prefix_ranges(999, 100), [])

    def test_filter_query_and_params(self):
        filt = layer2.PGCPrefixFilter(12, 200000)
        self.assertEqual(
            filt.get_query(),
            "(pgc >= %s AND pgc < %s) OR (pgc >= %s AND pgc < %s) OR "
            "(pgc >= %s AND pgc < %s) OR (pgc >= %s AND pgc < %s) OR "
            "(pgc >= %s AND pgc < %s)",
        )
        self.assertEqual(
            filt.get_params(),
            [12, 13, 120, 130, 1200, 1300, 12000, 13000, 120000, 130000],
        )
        self.assertEqual(filt.driving_table(), "(SELECT id AS pgc FROM common.pgc) AS pgc_drive")

    def test_filter_false_when_no_ranges(self):
        filt = layer2.PGCPrefixFilter(999, 100)
        self.assertEqual(filt.get_query(), "FALSE")
        self.assertEqual(filt.get_params(), [])
