import unittest
from dataclasses import dataclass
from unittest import mock

from app import commands
from app.data import model as data_model
from app.domain import actions
from app.domain import model as domain_model
from app.domain.actions.create_table import domain_descriptions_to_data, get_source_id
from app.lib import auth
from app.lib.web import errors


class GetSourceIDTest(unittest.TestCase):
    def test_get_source_id(self):
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

        with self.assertRaises(errors.RuleValidationError):
            _ = get_source_id(common_repo, ads_client, "2000A&A...534A..31G")

    def test_internal_comms_not_found(self):
        common_repo = mock.MagicMock()
        common_repo.get_source_entry.side_effect = RuntimeError("Not found")
        ads_client = mock.MagicMock()

        with self.assertRaises(errors.RuleValidationError):
            _ = get_source_id(common_repo, ads_client, "some_internal_code")


class MappingTest(unittest.TestCase):
    def test_mapping(self):
        @dataclass
        class TestData:
            name: str
            input_columns: list[domain_model.ColumnDescription]
            expected: list[data_model.ColumnDescription]
            err_substr: str | None

        tests = [
            TestData(
                "simple column",
                [domain_model.ColumnDescription("name", "str", "m / s", "description")],
                [data_model.ColumnDescription("name", "text", "m / s", "description")],
                None,
            ),
            TestData(
                "wrong type",
                [domain_model.ColumnDescription("name", "obscure_type", "m / s", "description")],
                [],
                "unknown type of data",
            ),
            TestData(
                "wrong unit",
                [domain_model.ColumnDescription("name", "str", "wrong", "description")],
                [],
                "unknown unit",
            ),
            TestData(
                "unit is None",
                [domain_model.ColumnDescription("name", "str", None, "description")],
                [data_model.ColumnDescription("name", "text", None, "description")],
                None,
            ),
            TestData(
                "unit has extra spaces",
                [domain_model.ColumnDescription("name", "str", "m     /       s", "description")],
                [data_model.ColumnDescription("name", "text", "m / s", "description")],
                None,
            ),
            TestData(
                "data type has extra spaces",
                [domain_model.ColumnDescription("name", "   str    ", None, "description")],
                [data_model.ColumnDescription("name", "text", None, "description")],
                None,
            ),
        ]

        for tc in tests:
            with self.subTest(tc.name):
                if tc.err_substr:
                    with self.assertRaises(errors.RuleValidationError) as err:
                        _ = domain_descriptions_to_data(tc.input_columns)

                    self.assertIn(tc.err_substr, err.exception.message())
                else:
                    self.assertEqual(domain_descriptions_to_data(tc.input_columns), tc.expected)


class CreateTableTest(unittest.TestCase):
    def setUp(self):
        self.common_repo_mock = mock.MagicMock()
        self.layer0_repo_mock = mock.MagicMock()
        self.queue_repo_mock = mock.MagicMock()
        self.clients_mock = mock.MagicMock()
        self.ads_mock = mock.MagicMock()
        self.clients_mock.ads_client = self.ads_mock

        depot = commands.Depot(
            self.common_repo_mock,
            self.layer0_repo_mock,
            self.queue_repo_mock,
            auth.NoopAuthenticator(),
            self.clients_mock,
        )

        self.depot = depot

    def test_create_table(self):
        @dataclass
        class TestData:
            name: str
            table_exists: bool
            expected_created: bool

        tests = [
            TestData(
                "create new table",
                False,
                True,
            ),
            TestData(
                "create already existing table",
                True,
                False,
            ),
        ]

        for tc in tests:
            with self.subTest(tc.name):
                self.common_repo_mock.get_source_entry.return_value.id = 41
                self.layer0_repo_mock.create_table.return_value = 51, not tc.table_exists

                resp, created = actions.create_table(
                    self.depot,
                    domain_model.CreateTableRequest(
                        "test",
                        [],
                        "totally real source id",
                        "regular",
                        "",
                    ),
                )
                self.assertEqual(51, resp.id)
                self.assertEqual(tc.expected_created, created)
