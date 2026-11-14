from typing import Any
from unittest import mock
from uuid import uuid4

import pytest

from app.adminapi.domain.layer1_write import Layer1Writer
from app.catalogs import layer0
from app.catalogs.layer1 import DesignationCatalogObject, ICRSCatalogObject
from app.lib.storage import postgres
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi


def test_designation_save_normalizes_design() -> None:
    repo = mock.Mock()
    repo.get_column_units.return_value = {}
    writer = Layer1Writer(repo, mock.Mock())

    request = adminapi.SaveStructuredDataRequest(
        catalog="designation",
        columns=["design"],
        ids=["r1"],
        data=[["ngc905"]],
    )
    writer.save_data(request)

    repo.save_structured_data.assert_called_once_with(
        DesignationCatalogObject.layer1_table(),
        ["design"],
        ["r1"],
        [["NGC 905"]],
        conflict_keys=DesignationCatalogObject.layer1_primary_keys(),
    )


def test_designation_save_preserves_already_normalized_design() -> None:
    repo = mock.Mock()
    repo.get_column_units.return_value = {}
    writer = Layer1Writer(repo, mock.Mock())

    request = adminapi.SaveStructuredDataRequest(
        catalog="designation",
        columns=["design"],
        ids=["r1"],
        data=[["NGC 905"]],
    )
    writer.save_data(request)

    repo.save_structured_data.assert_called_once_with(
        DesignationCatalogObject.layer1_table(),
        ["design"],
        ["r1"],
        [["NGC 905"]],
        conflict_keys=DesignationCatalogObject.layer1_primary_keys(),
    )


def test_non_designation_save_is_unaffected() -> None:
    repo = mock.Mock()
    repo.get_column_units.return_value = {"ra": "deg", "dec": "deg"}
    writer = Layer1Writer(repo, mock.Mock())

    request = adminapi.SaveStructuredDataRequest(
        catalog="icrs",
        columns=["ra", "dec"],
        units={"ra": "deg", "dec": "deg"},
        ids=["r1"],
        data=[[12.1, 0.1]],
    )
    writer.save_data(request)

    repo.save_structured_data.assert_called_once_with(
        ICRSCatalogObject.layer1_table(),
        ["ra", "dec"],
        ["r1"],
        [[12.1, 0.1]],
        conflict_keys=ICRSCatalogObject.layer1_primary_keys(),
    )


def test_start_upload() -> None:
    run_id = str(uuid4())
    prefect = mock.Mock()
    prefect.create_flow_run.return_value = run_id
    writer = Layer1Writer(mock.Mock(), prefect)
    params = {"table_name": "raw", "ra": 'col("ra")'}

    assert writer.start_upload(adminapi.StartStructuredUploadRequest(catalog="icrs", params=params)).task_id == run_id
    prefect.create_flow_run.assert_called_once_with(
        name="ICRS/upload-icrs",
        parameters={"params": params},
    )
    with pytest.raises(NotFoundError):
        writer.start_upload(adminapi.StartStructuredUploadRequest(catalog="missing", params=params))


_PREVIEW_ID = layer0.INTERNAL_ID_COLUMN_NAME


def _preview_table(schema: str, name: str, columns: list[postgres.ColumnInfo]) -> postgres.TableInfo:
    return postgres.TableInfo(schema=schema, name=name, columns={c.name: c for c in columns})


def _preview_col(name: str, data_type: str, unit: str | None = None, not_null: bool = False) -> postgres.ColumnInfo:
    return postgres.ColumnInfo(name=name, data_type=data_type, unit=unit, not_null=not_null)


def _run_preview(
    expressions: dict[str, str],
    rows: list[dict[str, Any]],
) -> adminapi.PreviewStructuredUploadResponse:
    tables = {
        ("icrs", "data"): _preview_table(
            "icrs",
            "data",
            [
                _preview_col("record_id", "text", not_null=True),
                _preview_col("ra", "double precision", "deg", True),
                _preview_col("dec", "double precision", "deg", True),
            ],
        ),
        ("rawdata", "raw"): _preview_table(
            "rawdata",
            "raw",
            [
                _preview_col(_PREVIEW_ID, "text"),
                _preview_col("ra_h", "double precision", "hourangle"),
                _preview_col("dec_d", "double precision", "deg"),
            ],
        ),
    }
    repo = mock.Mock()
    repo.get_table_metadata.side_effect = lambda schema, table: tables.get(
        (schema, table), _preview_table(schema, table, [])
    )
    repo.sample_rawdata.return_value = rows
    request = adminapi.PreviewStructuredUploadRequest(catalog="icrs", table_name="raw", expressions=expressions)
    return Layer1Writer(repo, mock.Mock()).preview_upload(request)


def _preview_row(record_id: str, ra_h: float | None, dec_d: float | None) -> dict[str, Any]:
    return {_PREVIEW_ID: record_id, "ra_h": ra_h, "dec_d": dec_d}


def test_preview_success() -> None:
    response = _run_preview(
        {"ra": 'col("ra_h")', "dec": 'col("dec_d")', "e_ra": ""},
        [_preview_row("r1", 12.0, 30.0), _preview_row("r2", 6.0, -10.0)],
    )

    assert response.errors == []
    assert [r.record_id for r in response.rows] == ["r1", "r2"]
    assert response.rows[0].inputs == {"dec_d": 30.0, "ra_h": 12.0}
    assert response.rows[0].outputs == pytest.approx({"ra": 180.0, "dec": 30.0})
    assert response.rows[1].outputs == pytest.approx({"ra": 90.0, "dec": -10.0})


def test_preview_syntax_error_does_not_affect_other_fields() -> None:
    response = _run_preview({"ra": 'col("ra_h")', "dec": "col("}, [_preview_row("r1", 12.0, 30.0)])

    assert [e.field for e in response.errors] == ["dec"]
    assert response.rows[0].outputs == pytest.approx({"ra": 180.0})


def test_preview_missing_column() -> None:
    response = _run_preview({"ra": 'col("ra_h")', "dec": 'col("nope")'}, [_preview_row("r1", 12.0, 30.0)])

    assert len(response.errors) == 1
    assert response.errors[0].field == "dec"
    assert "nope" in response.errors[0].message
    assert set(response.rows[0].outputs) == {"ra"}


def test_preview_row_failure_locates_record() -> None:
    response = _run_preview(
        {"ra": 'col("ra_h")', "dec": 'col("dec_d") / (col("dec_d") - 20 * deg) * deg'},
        [_preview_row("r1", 12.0, 30.0), _preview_row("r2", 6.0, 20.0), _preview_row("r3", 3.0, 40.0)],
    )

    assert len(response.errors) == 1
    error = response.errors[0]
    assert error.field == "dec"
    assert error.record_id == "r2"
    assert all("dec" not in row.outputs for row in response.rows)
    assert all("ra" in row.outputs for row in response.rows)


def test_preview_skips_rows_with_nulls() -> None:
    response = _run_preview(
        {"ra": 'col("ra_h")', "dec": 'col("dec_d")'},
        [_preview_row("r1", 12.0, 30.0), _preview_row("r2", 6.0, None)],
    )

    assert response.errors == []
    assert response.rows[0].skipped_reason is None
    assert response.rows[1].skipped_reason == "null in dec_d"
    assert response.rows[1].outputs == {}


def test_preview_unknown_catalog_and_field() -> None:
    repo = mock.Mock()
    with pytest.raises(NotFoundError):
        Layer1Writer(repo, mock.Mock()).preview_upload(
            adminapi.PreviewStructuredUploadRequest(catalog="nope", table_name="raw", expressions={})
        )
    with pytest.raises(RuleValidationError):
        _run_preview({"bogus": "1"}, [])
