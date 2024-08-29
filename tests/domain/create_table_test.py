import unittest
from dataclasses import dataclass
from unittest import mock

from parameterized import param, parameterized

from app import commands, schema
from app.data import model as data_model
from app.domain import actions
from app.domain.actions.create_table import INTERNAL_ID_COLUMN_NAME, domain_descriptions_to_data, get_source_id
from app.lib import auth
from app.lib.storage import mapping
from app.lib.web import errors


class GetSourceIDTest(unittest.TestCase):
    @parameterized.expand(
        [
            param("1982euse.book.....L", True),
            param("1975ApJS...45..113M", True),
            param("2011A&A...534A..31G", True),
            param("2011A&A.....31G", False),
            param("some_custom_code", False),
        ]
    )
    def test_get_source_id(self, code: str, ads_query_needed: bool):
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

        result = get_source_id(common_repo, ads_client, code)
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
    @dataclass
    class TestData:
        name: str
        input_columns: list[schema.ColumnDescription]
        expected: list[data_model.ColumnDescription] | None = None
        err_substr: str | None = None

    internal_id_column = data_model.ColumnDescription(
        name=INTERNAL_ID_COLUMN_NAME,
        data_type=mapping.TYPE_TEXT,
        is_primary_key=True,
    )

    @parameterized.expand(
        [
            param(
                "simple column",
                [
                    schema.ColumnDescription(
                        "name", "str", ucd="phys.veloc.orbital", unit="m / s", description="description"
                    )
                ],
                [
                    internal_id_column,
                    data_model.ColumnDescription(
                        "name", "text", ucd="phys.veloc.orbital", unit="m / s", description="description"
                    ),
                ],
            ),
            param(
                "wrong type",
                [schema.ColumnDescription("name", "obscure_type", unit="m / s")],
                err_substr="unknown type of data",
            ),
            param(
                "wrong unit",
                [schema.ColumnDescription("name", "str", unit="wrong")],
                err_substr="unknown unit",
            ),
            param(
                "unit is None",
                [schema.ColumnDescription("name", "str")],
                [internal_id_column, data_model.ColumnDescription("name", "text")],
            ),
            param(
                "unit has extra spaces",
                [schema.ColumnDescription("name", "str", unit="m     /       s")],
                [internal_id_column, data_model.ColumnDescription("name", "text", unit="m / s")],
            ),
            param(
                "data type has extra spaces",
                [schema.ColumnDescription("name", "   str    ")],
                [internal_id_column, data_model.ColumnDescription("name", "text", unit=None)],
            ),
            param(
                "invalid ucd",
                [schema.ColumnDescription("name", "str", ucd="totally invalid ucd")],
                err_substr="invalid or unknown UCD",
            ),
        ],
    )
    def test_mapping(
        self,
        name: str,
        input_columns: list[schema.ColumnDescription],
        expected: list[data_model.ColumnDescription] | None = None,
        err_substr: str | None = None,
    ):
        if err_substr:
            with self.assertRaises(errors.RuleValidationError) as err:
                _ = domain_descriptions_to_data(input_columns)

            self.assertIn(err_substr, err.exception.message())
        else:
            self.assertEqual(domain_descriptions_to_data(input_columns), expected)


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
            mock.MagicMock(),
            mock.MagicMock(),
            self.queue_repo_mock,
            auth.NoopAuthenticator(),
            self.clients_mock,
        )

        self.depot = depot

    @parameterized.expand(
        [
            param(
                "create new table",
                schema.CreateTableRequest("test", [], "totally real bibcode", "regular", ""),
            ),
            param(
                "create already existing table",
                schema.CreateTableRequest("test", [], "totally real bibcode", "regular", ""),
                table_already_existed=True,
                expected_created=False,
            ),
            param(
                "create table with forbidden name",
                schema.CreateTableRequest(
                    "test",
                    [schema.ColumnDescription("hyperleda_internal_id", "str", None, "")],
                    "totally real bibcode",
                    "regular",
                    "",
                ),
                err_substr="is a reserved column name for internal storage",
            ),
        ],
    )
    def test_create_table(
        self,
        name: str,
        request: schema.CreateTableRequest,
        table_already_existed: bool = False,
        expected_created: bool = True,
        err_substr: str | None = None,
    ):
        self.common_repo_mock.get_source_entry.return_value.id = 41
        self.layer0_repo_mock.create_table.return_value = data_model.Layer0CreationResponse(
            51, not table_already_existed
        )

        if err_substr is not None:
            with self.assertRaises(errors.RuleValidationError) as err:
                _, _ = actions.create_table(
                    self.depot,
                    request,
                )

            self.assertIn(err_substr, err.exception.message())
        else:
            resp, created = actions.create_table(
                self.depot,
                request,
            )
            self.assertEqual(51, resp.id)
            self.assertEqual(expected_created, created)
