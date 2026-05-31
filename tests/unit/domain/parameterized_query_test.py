import unittest

from app.data import model
from app.domain.dataapi import parameterized_query

DEFAULT = [
    model.RawCatalog.DESIGNATION,
    model.RawCatalog.ICRS,
    model.RawCatalog.REDSHIFT,
]


class ResolveQueryCatalogsTest(unittest.TestCase):
    def test_none_returns_default(self):
        self.assertEqual(
            parameterized_query.resolve_query_catalogs(None, DEFAULT),
            DEFAULT,
        )

    def test_subset_preserves_request_order(self):
        self.assertEqual(
            parameterized_query.resolve_query_catalogs(
                ["icrs", "designation"],
                DEFAULT,
            ),
            [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION],
        )

    def test_deduplicates(self):
        self.assertEqual(
            parameterized_query.resolve_query_catalogs(
                ["icrs", "icrs"],
                DEFAULT,
            ),
            [model.RawCatalog.ICRS],
        )

    def test_empty_list_raises(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            parameterized_query.resolve_query_catalogs([], DEFAULT)

    def test_unknown_catalog_raises(self):
        with self.assertRaisesRegex(ValueError, "Unknown catalog"):
            parameterized_query.resolve_query_catalogs(["not_a_catalog"], DEFAULT)

    def test_unavailable_catalog_raises(self):
        with self.assertRaisesRegex(ValueError, "not available"):
            parameterized_query.resolve_query_catalogs(
                ["note"],
                DEFAULT,
            )
