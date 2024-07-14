import unittest
from unittest import mock

from app.data import model as data_model
from app.domain import model as domain_model
from app.domain.actions.create_table import domain_descriptions_to_data, get_source_id
from app.lib import exceptions


class GetSourceIDTest(unittest.TestCase):
    def test_branching(self):
        tests = [
            ("1982euse.book.....L", True),
            ("1975ApJS...45..113M", True),
            ("2011A&A...534A..31G", True),
            ("2011A&A.....31G", False),
            ("some_custom_code", False),
        ]

        common_repo = mock.MagicMock()
        common_repo.create_bibliography.return_value = 41
        common_repo.get_source_entry.return_value.id = 42
        ads_client = mock.MagicMock()
        ads_client.query_simple.return_value = [
            {
                "title": ["Some Title"],
                "author": ["Author1", "Author2"],
                "pubdate": "2011-01-00",
            }
        ]

        for source_name, ads_query_needed in tests:
            with self.subTest(source_name):
                result = get_source_id(common_repo, ads_client, source_name)
                if ads_query_needed:
                    self.assertEqual(result, 41)
                else:
                    self.assertEqual(result, 42)

    def test_ads_not_found(self):
        common_repo = mock.MagicMock()
        ads_client = mock.MagicMock()
        ads_client.query_simple.side_effect = RuntimeError("Not found")

        with self.assertRaises(exceptions.APIException):
            _ = get_source_id(common_repo, ads_client, "2000A&A...534A..31G")

    def test_internal_comms_not_found(self):
        common_repo = mock.MagicMock()
        common_repo.get_source_entry.side_effect = RuntimeError("Not found")
        ads_client = mock.MagicMock()

        with self.assertRaises(exceptions.APIException):
            _ = get_source_id(common_repo, ads_client, "some_internal_code")


class MappingTest(unittest.TestCase):
    def test_mapping(self):
        tests = [
            (
                "normal run",
                [domain_model.ColumnDescription("name", "str", "m / s", "description")],
                [data_model.ColumnDescription("name", "text", "m / s", "description")],
                None,
            ),
            (
                "wrong type",
                [domain_model.ColumnDescription("name", "obscure_type", "m / s", "description")],
                [],
                "unknown type of data",
            ),
            (
                "wrong unit",
                [domain_model.ColumnDescription("name", "str", "wrong", "description")],
                [],
                "unknown unit",
            ),
            (
                "unit is None",
                [domain_model.ColumnDescription("name", "str", None, "description")],
                [data_model.ColumnDescription("name", "text", None, "description")],
                None,
            ),
            (
                "unit has extra spaces",
                [domain_model.ColumnDescription("name", "str", "m     /       s", "description")],
                [data_model.ColumnDescription("name", "text", "m / s", "description")],
                None,
            ),
            (
                "data type has extra spaces",
                [domain_model.ColumnDescription("name", "   str    ", None, "description")],
                [data_model.ColumnDescription("name", "text", None, "description")],
                None,
            ),
        ]

        for name, input_columns, expected, err_message_substr in tests:
            with self.subTest(name):
                if err_message_substr:
                    with self.assertRaises(exceptions.APIException) as err:
                        _ = domain_descriptions_to_data(input_columns)

                    self.assertIn(err_message_substr, err.exception.message)
                else:
                    self.assertEqual(domain_descriptions_to_data(input_columns), expected)
