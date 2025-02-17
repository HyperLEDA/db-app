import unittest
from dataclasses import dataclass
from unittest import mock

from parameterized import param, parameterized

from app.data import model, repositories
from app.domain import adminapi as domain
from app.domain.adminapi.table_upload import domain_descriptions_to_data, get_source_id
from app.lib import clients
from app.lib.storage import mapping
from app.lib.web import errors
from app.presentation import adminapi as presentation
from tests import lib


class TableUploadManagerTest(unittest.TestCase):
    def setUp(self):
        self.manager = domain.TableUploadManager(
            common_repo=mock.MagicMock(),
            layer0_repo=mock.MagicMock(),
            clients=clients.get_mock_clients(),
        )

    def test_add_data(self):
        request = presentation.AddDataRequest(
            42,
            data=[
                {
                    "test": "row",
                    "number": 41,
                },
                {
                    "test": "row2",
                    "number": 43,
                },
            ],
        )

        _ = self.manager.add_data(request)

        request = self.manager.layer0_repo.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row", "row2"])
        self.assertListEqual(list(request.args[0].data["number"]), [41, 43])
        self.assertListEqual(
            list(request.args[0].data["hyperleda_internal_id"]),
            ["e75d9505-36d1-26c6-23e9-54f663ce35a2", "27fb0c18-b72b-3457-0bff-56b40182638a"],
        )

    def test_add_data_identical_rows(self):
        request = presentation.AddDataRequest(
            42,
            data=[
                {
                    "test": "row",
                    "number": 41,
                },
                {
                    "test": "row",
                    "number": 41,
                },
            ],
        )

        _ = self.manager.add_data(request)

        request = self.manager.layer0_repo.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row"])
        self.assertListEqual(list(request.args[0].data["number"]), [41])

    @parameterized.expand(
        [
            param(
                "create new table",
                presentation.CreateTableRequest(
                    "test",
                    [
                        presentation.ColumnDescription("objname", "str", ucd="meta.id"),
                        presentation.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit="h"),
                        presentation.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit="h"),
                    ],
                    "totally real bibcode",
                    "regular",
                    "",
                ),
            ),
            param(
                "create already existing table",
                presentation.CreateTableRequest(
                    "test",
                    [
                        presentation.ColumnDescription("objname", "str", ucd="meta.id"),
                        presentation.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit="h"),
                        presentation.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit="h"),
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
                presentation.CreateTableRequest(
                    "test",
                    [presentation.ColumnDescription("hyperleda_internal_id", "str", None, "")],
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
        request: presentation.CreateTableRequest,
        table_already_existed: bool = False,
        expected_created: bool = True,
        err_substr: str | None = None,
    ):
        lib.returns(self.manager.common_repo.create_bibliography, 41)
        lib.returns(self.manager.layer0_repo.create_table, model.Layer0CreationResponse(51, not table_already_existed))

        if err_substr is not None:
            with self.assertRaises(errors.RuleValidationError) as err:
                _, _ = self.manager.create_table(request)

            self.assertIn(err_substr, err.exception.message())
        else:
            resp, created = self.manager.create_table(request)
            self.assertEqual(51, resp.id)
            self.assertEqual(expected_created, created)


class GetSourceIDTest(unittest.TestCase):
    def setUp(self):
        self.manager = domain.TableUploadManager(
            common_repo=mock.MagicMock(),
            layer0_repo=mock.MagicMock(),
            clients=clients.get_mock_clients(),
        )

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
        lib.returns(self.manager.common_repo.create_bibliography, 41)
        lib.returns(self.manager.common_repo.get_source_entry, mock.MagicMock(id=42))
        lib.returns(
            self.manager.clients.ads.query_simple,
            [
                {
                    "title": ["Some Title"],
                    "author": ["Author1", "Author2"],
                    "pubdate": "2011-01-00",
                }
            ],
        )

        result = get_source_id(self.manager.common_repo, self.manager.clients.ads, code)
        if ads_query_needed:
            self.assertEqual(result, 41)
        else:
            self.assertEqual(result, 42)

    def test_ads_not_found(self):
        lib.raises(self.manager.clients.ads.query_simple, RuntimeError("Not found"))

        with self.assertRaises(errors.RuleValidationError):
            _ = get_source_id(self.manager.common_repo, self.manager.clients.ads, "2000A&A...534A..31G")

    def test_internal_comms_not_found(self):
        lib.raises(self.manager.common_repo.get_source_entry, RuntimeError("Not found"))
        ads_client = mock.MagicMock()

        with self.assertRaises(errors.RuleValidationError):
            _ = get_source_id(self.manager.common_repo, ads_client, "some_internal_code")


class MappingTest(unittest.TestCase):
    @dataclass
    class TestData:
        name: str
        input_columns: list[presentation.ColumnDescription]
        expected: list[model.ColumnDescription] | None = None
        err_substr: str | None = None

    internal_id_column = model.ColumnDescription(
        name=repositories.INTERNAL_ID_COLUMN_NAME,
        data_type=mapping.TYPE_TEXT,
        is_primary_key=True,
    )

    @parameterized.expand(
        [
            param(
                "simple column",
                [
                    presentation.ColumnDescription(
                        "name", "str", ucd="phys.veloc.orbital", unit="m / s", description="description"
                    )
                ],
                [
                    internal_id_column,
                    model.ColumnDescription(
                        "name", "text", ucd="phys.veloc.orbital", unit="m / s", description="description"
                    ),
                ],
            ),
            param(
                "wrong type",
                [presentation.ColumnDescription("name", "obscure_type", unit="m / s")],
                err_substr="unknown type of data",
            ),
            param(
                "wrong unit",
                [presentation.ColumnDescription("name", "str", unit="wrong")],
                err_substr="unknown unit",
            ),
            param(
                "unit is None",
                [presentation.ColumnDescription("name", "str")],
                [internal_id_column, model.ColumnDescription("name", "text")],
            ),
            param(
                "unit has extra spaces",
                [presentation.ColumnDescription("name", "str", unit="m     /       s")],
                [internal_id_column, model.ColumnDescription("name", "text", unit="m / s")],
            ),
            param(
                "data type has extra spaces",
                [presentation.ColumnDescription("name", "   str    ")],
                [internal_id_column, model.ColumnDescription("name", "text", unit=None)],
            ),
            param(
                "invalid ucd",
                [presentation.ColumnDescription("name", "str", ucd="totally invalid ucd")],
                err_substr="invalid or unknown UCD",
            ),
        ],
    )
    def test_mapping(
        self,
        name: str,
        input_columns: list[presentation.ColumnDescription],
        expected: list[model.ColumnDescription] | None = None,
        err_substr: str | None = None,
    ):
        if err_substr:
            with self.assertRaises(errors.RuleValidationError) as err:
                _ = domain_descriptions_to_data(input_columns)

            self.assertIn(err_substr, err.exception.message())
        else:
            self.assertEqual(domain_descriptions_to_data(input_columns), expected)
