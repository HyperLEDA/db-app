import unittest
from dataclasses import dataclass
from unittest import mock

from astropy import units
from parameterized import param, parameterized

from app.adminapi import clients, domain, model, repository
from app.adminapi.domain.mock import get_mock_table_stats_cache
from app.adminapi.domain.table_upload import domain_descriptions_to_data, ensure_source_id
from app.lib.storage import enums, mapping, postgres
from app.lib.web import errors
from app.specs import adminapi
from tests import lib


class TableUploadManagerTest(unittest.TestCase):
    def setUp(self):
        self.repo = mock.MagicMock()
        self.manager = domain.TableUploadManager(
            self.repo,
            clients=clients.get_mock_clients(),
            table_stats_cache=get_mock_table_stats_cache(),
        )

    def test_add_data(self):
        request = adminapi.AddDataRequest(
            table_name="test_table",
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

        request = self.repo.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row", "row2"])
        self.assertListEqual(list(request.args[0].data["number"]), [41, 43])
        self.assertListEqual(
            list(request.args[0].data["hyperleda_internal_id"]),
            ["1b4bbb6e-27d8-f7b8-2a5e-3a37b1c3248e", "a62b5fd9-9b6a-964c-406d-3fa4fc3471d7"],
        )

    def test_add_data_identical_rows(self):
        request = adminapi.AddDataRequest(
            table_name="test_table",
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

        request = self.repo.insert_raw_data.call_args

        self.assertListEqual(list(request.args[0].data["test"]), ["row"])
        self.assertListEqual(list(request.args[0].data["number"]), [41])

    @parameterized.expand(
        [
            param(
                "create new table",
                adminapi.CreateTableRequest(
                    table_name="test",
                    columns=[
                        adminapi.ColumnDescription(
                            name="objname", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id"
                        ),
                        adminapi.ColumnDescription(
                            name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                        ),
                        adminapi.ColumnDescription(
                            name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                        ),
                    ],
                    bibcode="totally real bibcode",
                    datatype=enums.DataType.REGULAR,
                    description="",
                ),
            ),
            param(
                "create already existing table",
                adminapi.CreateTableRequest(
                    table_name="test",
                    columns=[
                        adminapi.ColumnDescription(
                            name="objname", data_type=adminapi.DatatypeEnum["str"], ucd="meta.id"
                        ),
                        adminapi.ColumnDescription(
                            name="ra", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.ra", unit="h"
                        ),
                        adminapi.ColumnDescription(
                            name="dec", data_type=adminapi.DatatypeEnum["float"], ucd="pos.eq.dec", unit="h"
                        ),
                    ],
                    bibcode="totally real bibcode",
                    datatype=enums.DataType.REGULAR,
                    description="",
                ),
                table_already_existed=True,
                expected_created=False,
            ),
        ],
    )
    def test_create_table(
        self,
        _: str,
        request: adminapi.CreateTableRequest,
        table_already_existed: bool = False,
        expected_created: bool = True,
        err_substr: str | None = None,
    ):
        lib.returns(self.repo.create_bibliography, 41)
        lib.returns(self.repo.create_table, model.Layer0CreationResponse(51, not table_already_existed))

        if err_substr is not None:
            with self.assertRaises(errors.RuleValidationError) as err:
                self.manager.create_table(request)

            self.assertIn(err_substr, err.exception.message())
        else:
            resp, created = self.manager.create_table(request)
            self.assertEqual(51, resp.id)
            self.assertEqual(expected_created, created)


class GetSourceIDTest(unittest.TestCase):
    def setUp(self):
        self.repo = mock.MagicMock()
        self.manager = domain.TableUploadManager(
            self.repo,
            clients=clients.get_mock_clients(),
            table_stats_cache=get_mock_table_stats_cache(),
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
    def test_ensure_source_id(self, code: str, ads_query_needed: bool):
        lib.returns(self.repo.create_bibliography, 41)
        lib.returns(self.repo.get_source_entry, mock.MagicMock(id=42))
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

        result = ensure_source_id(self.repo, self.manager.clients.ads, code)
        if ads_query_needed:
            self.assertEqual(result, 41)
        else:
            self.assertEqual(result, 42)

    def test_ads_not_found(self):
        lib.raises(self.manager.clients.ads.query_simple, RuntimeError("Not found"))

        with self.assertRaises(errors.RuleValidationError):
            _ = ensure_source_id(self.repo, self.manager.clients.ads, "2000A&A...534A..31G")

    def test_internal_comms_not_found(self):
        lib.raises(self.repo.get_source_entry, RuntimeError("Not found"))
        ads_client = mock.MagicMock()

        with self.assertRaises(errors.RuleValidationError):
            _ = ensure_source_id(self.repo, ads_client, "some_internal_code")


class MappingTest(unittest.TestCase):
    @dataclass
    class TestData:
        name: str
        input_columns: list[adminapi.ColumnDescription]
        expected: list[model.ColumnDescription] | None = None
        err_substr: str | None = None

    internal_id_column = model.ColumnDescription(
        name=repository.INTERNAL_ID_COLUMN_NAME,
        data_type=mapping.TYPE_TEXT,
        is_primary_key=True,
    )

    @parameterized.expand(
        [
            param(
                "simple column",
                [
                    adminapi.ColumnDescription(
                        name="name",
                        data_type=adminapi.DatatypeEnum["str"],
                        ucd="phys.veloc.orbital",
                        unit="m / s",
                        description="description",
                    )
                ],
                [
                    internal_id_column,
                    model.ColumnDescription(
                        "name", "text", ucd="phys.veloc.orbital", unit=units.Unit("m / s"), description="description"
                    ),
                ],
            ),
            param(
                "unit is None",
                [adminapi.ColumnDescription(name="name", data_type=adminapi.DatatypeEnum["str"])],
                [internal_id_column, model.ColumnDescription("name", "text")],
            ),
            param(
                "unit has extra spaces",
                [
                    adminapi.ColumnDescription(
                        name="name", data_type=adminapi.DatatypeEnum["str"], unit="m     /       s"
                    )
                ],
                [internal_id_column, model.ColumnDescription("name", "text", unit=units.Unit("m / s"))],
            ),
            param(
                "invalid unit is ignored and appended to description",
                [
                    adminapi.ColumnDescription(
                        name="name",
                        data_type=adminapi.DatatypeEnum["str"],
                        unit="not_a_unit",
                        description="some description",
                    )
                ],
                [
                    internal_id_column,
                    model.ColumnDescription(
                        "name", "text", unit=None, description="some description (unit not_a_unit)"
                    ),
                ],
            ),
            param(
                "invalid unit with no description",
                [
                    adminapi.ColumnDescription(
                        name="name",
                        data_type=adminapi.DatatypeEnum["str"],
                        unit="not_a_unit",
                    )
                ],
                [
                    internal_id_column,
                    model.ColumnDescription("name", "text", unit=None, description="(unit not_a_unit)"),
                ],
            ),
        ],
    )
    def test_mapping(
        self,
        _: str,
        input_columns: list[adminapi.ColumnDescription],
        expected: list[model.ColumnDescription] | None = None,
        err_substr: str | None = None,
    ):
        if err_substr:
            with self.assertRaises(errors.RuleValidationError) as err:
                domain_descriptions_to_data(input_columns)

            self.assertIn(err_substr, err.exception.message())
        else:
            self.assertEqual(domain_descriptions_to_data(input_columns), expected)


class GetRecordsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = mock.MagicMock()
        self.repo.get_table_metadata.return_value = postgres.TableInfo(
            schema="",
            name="",
            description=None,
            columns={},
            primary_keys=set(),
        )
        self.repo.get_designation_records.side_effect = lambda record_ids: [None] * len(record_ids)
        self.repo.get_icrs_records.side_effect = lambda record_ids: [None] * len(record_ids)
        self.repo.get_redshift_records.side_effect = lambda record_ids: [None] * len(record_ids)
        self.repo.get_nature_records.side_effect = lambda record_ids: [None] * len(record_ids)
        self.manager = domain.TableUploadManager(
            self.repo,
            clients=clients.get_mock_clients(),
            table_stats_cache=get_mock_table_stats_cache(),
        )

    def test_get_records_returns_records_with_pgc(self) -> None:
        self.repo.fetch_records.return_value = [
            model.TableRecord(
                id="rec1", original_data={"name": "A"}, pgc=1001, triage_status="resolved", crossmatch_candidates=[1001]
            ),
            model.TableRecord(
                id="rec2",
                original_data={"name": "B"},
                pgc=1002,
                triage_status="pending",
                crossmatch_candidates=[],
            ),
        ]

        request = adminapi.GetRecordsRequest(table_name="t", page=0, page_size=25)
        response = self.manager.get_records(request)

        self.assertEqual(len(response.records), 2)
        self.assertEqual(response.records[0].id, "rec1")
        self.assertEqual(response.records[0].original_data, {"name": "A"})
        self.assertEqual(response.records[0].pgc, 1001)
        self.assertEqual(response.records[0].crossmatch.triage_status, adminapi.CrossmatchTriageStatus.RESOLVED)
        self.assertEqual(
            response.records[0].crossmatch.candidates,
            [adminapi.RecordCrossmatchCandidate(pgc=1001)],
        )
        self.assertEqual(response.records[1].id, "rec2")
        self.assertEqual(response.records[1].original_data, {"name": "B"})
        self.assertEqual(response.records[1].pgc, 1002)
        self.assertEqual(response.records[1].crossmatch.triage_status, adminapi.CrossmatchTriageStatus.PENDING)
        self.assertEqual(response.records[1].crossmatch.candidates, [])

    def test_get_records_passes_filters_to_fetch_records(self) -> None:
        self.repo.fetch_records.return_value = []

        self.manager.get_records(
            adminapi.GetRecordsRequest(table_name="t", upload_status=adminapi.UploadStatus.UPLOADED)
        )
        call_kw = self.repo.fetch_records.call_args[1]
        self.assertIs(call_kw["has_pgc"], True)
        self.assertIsNone(call_kw["pgc_value"])

        self.manager.get_records(
            adminapi.GetRecordsRequest(table_name="t", upload_status=adminapi.UploadStatus.PENDING)
        )
        call_kw = self.repo.fetch_records.call_args[1]
        self.assertIs(call_kw["has_pgc"], False)

        self.manager.get_records(adminapi.GetRecordsRequest(table_name="t", pgc=42))
        call_kw = self.repo.fetch_records.call_args[1]
        self.assertIsNone(call_kw["has_pgc"])
        self.assertEqual(call_kw["pgc_value"], 42)

        self.manager.get_records(
            adminapi.GetRecordsRequest(table_name="t", triage_status=adminapi.CrossmatchTriageStatus.PENDING)
        )
        call_kw = self.repo.fetch_records.call_args[1]
        self.assertEqual(call_kw["triage_status"], "pending")

    def test_get_records_pagination(self) -> None:
        self.repo.fetch_records.return_value = []

        self.manager.get_records(adminapi.GetRecordsRequest(table_name="t", page=2, page_size=10))
        call_kw = self.repo.fetch_records.call_args[1]
        self.assertEqual(call_kw["row_offset"], 20)
        self.assertEqual(call_kw["limit"], 10)

    def test_get_records_pgc_none_when_missing(self) -> None:
        self.repo.fetch_records.return_value = [
            model.TableRecord(
                id="rec1",
                original_data={"name": "A"},
                pgc=1001,
                triage_status="resolved",
                crossmatch_candidates=[],
            ),
            model.TableRecord(
                id="rec2",
                original_data={"name": "B"},
                pgc=None,
                triage_status="unprocessed",
                crossmatch_candidates=[],
            ),
        ]

        response = self.manager.get_records(adminapi.GetRecordsRequest(table_name="t", page=0, page_size=25))

        self.assertEqual(response.records[0].pgc, 1001)
        self.assertIsNone(response.records[1].pgc)
