import re
import unittest
from unittest import mock

from astropy import units as u

from app.data import model
from app.data.repositories import layer2


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
            "CROSS JOIN layer2.designations LEFT JOIN layer2.designation USING (pgc) "
            "LEFT JOIN layer2.icrs USING (pgc) LEFT JOIN layer2.cz USING (pgc)",
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

        self.assertIn("CROSS JOIN layer2.designations LEFT JOIN layer2.cz USING (pgc)", query)
        self.assertNotIn('"designation|design"', query)
