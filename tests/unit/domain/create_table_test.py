import unittest
from dataclasses import dataclass
from unittest import mock

from parameterized import param, parameterized

from app import entities, schema
from app.commands.adminapi import depot
from app.data import repositories
from app.domain import actions
from app.domain.actions.create_table import domain_descriptions_to_data, get_source_id
from app.lib import testing
from app.lib.storage import mapping
from app.lib.web import errors


class GetSourceIDTest(unittest.TestCase):
    def setUp(self):
        self.depot = depot.get_mock_depot()

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
        testing.returns(self.depot.common_repo.create_bibliography, 41)
        testing.returns(self.depot.common_repo.get_source_entry, mock.MagicMock(id=42))
        testing.returns(
            self.depot.clients.ads.query_simple,
            [
                {
                    "title": ["Some Title"],
                    "author": ["Author1", "Author2"],
                    "pubdate": "2011-01-00",
                }
            ],
        )

        result = get_source_id(self.depot.common_repo, self.depot.clients.ads, code)
        if ads_query_needed:
            self.assertEqual(result, 41)
        else:
            self.assertEqual(result, 42)

    def test_ads_not_found(self):
        testing.raises(self.depot.clients.ads.query_simple, RuntimeError("Not found"))

        with self.assertRaises(errors.RuleValidationError):
            _ = get_source_id(self.depot.common_repo, self.depot.clients.ads, "2000A&A...534A..31G")

    def test_internal_comms_not_found(self):
        testing.raises(self.depot.common_repo.get_source_entry, RuntimeError("Not found"))
        ads_client = mock.MagicMock()

        with self.assertRaises(errors.RuleValidationError):
            _ = get_source_id(self.depot.common_repo, ads_client, "some_internal_code")


class MappingTest(unittest.TestCase):
    @dataclass
    class TestData:
        name: str
        input_columns: list[schema.ColumnDescription]
        expected: list[entities.ColumnDescription] | None = None
        err_substr: str | None = None

    internal_id_column = entities.ColumnDescription(
        name=repositories.INTERNAL_ID_COLUMN_NAME,
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
                    entities.ColumnDescription(
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
                [internal_id_column, entities.ColumnDescription("name", "text")],
            ),
            param(
                "unit has extra spaces",
                [schema.ColumnDescription("name", "str", unit="m     /       s")],
                [internal_id_column, entities.ColumnDescription("name", "text", unit="m / s")],
            ),
            param(
                "data type has extra spaces",
                [schema.ColumnDescription("name", "   str    ")],
                [internal_id_column, entities.ColumnDescription("name", "text", unit=None)],
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
        expected: list[entities.ColumnDescription] | None = None,
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
        self.depot = depot.get_mock_depot()

    @parameterized.expand(
        [
            param(
                "create new table",
                schema.CreateTableRequest(
                    "test",
                    [
                        schema.ColumnDescription("objname", "str", ucd="meta.id"),
                        schema.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit="h"),
                        schema.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit="h"),
                    ],
                    "totally real bibcode",
                    "regular",
                    "",
                ),
            ),
            param(
                "create already existing table",
                schema.CreateTableRequest(
                    "test",
                    [
                        schema.ColumnDescription("objname", "str", ucd="meta.id"),
                        schema.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit="h"),
                        schema.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit="h"),
                    ],
                    "totally real bibcode",
                    "regular",
                    "",
                ),
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
                err_substr="is a reserved column name",
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
        testing.returns(self.depot.common_repo.create_bibliography, 41)
        testing.returns(
            self.depot.layer0_repo.create_table, entities.Layer0CreationResponse(51, not table_already_existed)
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
