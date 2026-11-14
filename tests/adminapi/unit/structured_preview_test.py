from typing import Any
from unittest import mock

import pytest

from app.adminapi.domain import structured_preview
from app.catalogs import layer0
from app.lib.storage import postgres
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec

_ID = layer0.INTERNAL_ID_COLUMN_NAME


def _table(schema: str, name: str, columns: list[postgres.ColumnInfo]) -> postgres.TableInfo:
    return postgres.TableInfo(schema=schema, name=name, columns={c.name: c for c in columns})


def _col(name: str, data_type: str, unit: str | None = None, not_null: bool = False) -> postgres.ColumnInfo:
    return postgres.ColumnInfo(name=name, data_type=data_type, unit=unit, not_null=not_null)


def _preview(
    expressions: dict[str, str],
    rows: list[dict[str, Any]],
) -> spec.PreviewStructuredUploadResponse:
    tables = {
        ("icrs", "data"): _table(
            "icrs",
            "data",
            [
                _col("record_id", "text", not_null=True),
                _col("ra", "double precision", "deg", True),
                _col("dec", "double precision", "deg", True),
            ],
        ),
        ("rawdata", "raw"): _table(
            "rawdata",
            "raw",
            [
                _col(_ID, "text"),
                _col("ra_h", "double precision", "hourangle"),
                _col("dec_d", "double precision", "deg"),
            ],
        ),
    }
    repo = mock.Mock()
    repo.get_table_metadata.side_effect = lambda schema, table: tables.get((schema, table), _table(schema, table, []))
    repo.sample_rawdata.return_value = rows
    request = spec.PreviewStructuredUploadRequest(catalog="icrs", table_name="raw", expressions=expressions)
    return structured_preview.StructuredPreview(repo).preview(request)


def _row(record_id: str, ra_h: float | None, dec_d: float | None) -> dict[str, Any]:
    return {_ID: record_id, "ra_h": ra_h, "dec_d": dec_d}


def test_preview_success() -> None:
    response = _preview(
        {"ra": 'col("ra_h")', "dec": 'col("dec_d")', "e_ra": ""},
        [_row("r1", 12.0, 30.0), _row("r2", 6.0, -10.0)],
    )

    assert response.errors == []
    assert [r.record_id for r in response.rows] == ["r1", "r2"]
    assert response.rows[0].inputs == {"dec_d": 30.0, "ra_h": 12.0}
    assert response.rows[0].outputs == pytest.approx({"ra": 180.0, "dec": 30.0})
    assert response.rows[1].outputs == pytest.approx({"ra": 90.0, "dec": -10.0})


def test_preview_syntax_error_does_not_affect_other_fields() -> None:
    response = _preview({"ra": 'col("ra_h")', "dec": "col("}, [_row("r1", 12.0, 30.0)])

    assert [e.field for e in response.errors] == ["dec"]
    assert response.rows[0].outputs == pytest.approx({"ra": 180.0})


def test_preview_missing_column() -> None:
    response = _preview({"ra": 'col("ra_h")', "dec": 'col("nope")'}, [_row("r1", 12.0, 30.0)])

    assert len(response.errors) == 1
    assert response.errors[0].field == "dec"
    assert "nope" in response.errors[0].message
    assert set(response.rows[0].outputs) == {"ra"}


def test_preview_row_failure_locates_record() -> None:
    response = _preview(
        {"ra": 'col("ra_h")', "dec": 'col("dec_d") / (col("dec_d") - 20 * deg) * deg'},
        [_row("r1", 12.0, 30.0), _row("r2", 6.0, 20.0), _row("r3", 3.0, 40.0)],
    )

    assert len(response.errors) == 1
    error = response.errors[0]
    assert error.field == "dec"
    assert error.record_id == "r2"
    assert all("dec" not in row.outputs for row in response.rows)
    assert all("ra" in row.outputs for row in response.rows)


def test_preview_skips_rows_with_nulls() -> None:
    response = _preview(
        {"ra": 'col("ra_h")', "dec": 'col("dec_d")'},
        [_row("r1", 12.0, 30.0), _row("r2", 6.0, None)],
    )

    assert response.errors == []
    assert response.rows[0].skipped_reason is None
    assert response.rows[1].skipped_reason == "null in dec_d"
    assert response.rows[1].outputs == {}


def test_preview_unknown_catalog_and_field() -> None:
    repo = mock.Mock()
    with pytest.raises(NotFoundError):
        structured_preview.StructuredPreview(repo).preview(
            spec.PreviewStructuredUploadRequest(catalog="nope", table_name="raw", expressions={})
        )
    with pytest.raises(RuleValidationError):
        _preview({"bogus": "1"}, [])
