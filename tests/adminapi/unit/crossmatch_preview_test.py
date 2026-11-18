from unittest import mock

import pytest

from app.adminapi.domain.crossmatch import CrossmatchManager
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi


def _row(
    record_id: str,
    ra: float,
    dec: float,
    *,
    pgc: int | None = None,
    design: str | None = None,
) -> dict[str, object]:
    return {
        "new_id": record_id,
        "new_ra": ra,
        "new_dec": dec,
        "new_design": design,
        "new_cz": None,
        "new_type": None,
        "existing_pgc": pgc,
        "existing_ra": ra if pgc is not None else None,
        "existing_dec": dec if pgc is not None else None,
        "existing_design": design,
        "existing_cz": None,
        "existing_type": None,
    }


def test_preview_crossmatch_matches_sampled_records() -> None:
    repo = mock.Mock()
    repo.sample_crossmatch_records.return_value = (["near", "far"], 8)
    repo.fetch_crossmatch_neighbors.return_value = [
        _row("near", 10.0, 20.0, pgc=100, design="NGC 1"),
        _row("far", 180.0, 0.0),
    ]
    repo.pgcs_by_designation.return_value = {}

    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius=30, limit=2))

    by_id = {row.record_id: row for row in response.rows}
    assert response.total_count == 8
    assert by_id["near"].status == "existing" and by_id["near"].triage == "resolved"
    assert by_id["near"].candidates == [100] and by_id["near"].neighbors[0].pgc == 100
    assert by_id["near"].neighbors[0].ra == 10.0 and by_id["near"].neighbors[0].dec == 20.0
    assert by_id["near"].neighbors[0].distance_arcsec == 0
    assert by_id["far"].status == "new" and by_id["far"].candidates == []
    repo.fetch_claimed_pgcs.assert_not_called()
    repo.sample_crossmatch_records.assert_called_once_with("raw", 2)


def test_preview_crossmatch_missing_table() -> None:
    repo = mock.Mock()
    repo.sample_crossmatch_records.side_effect = RuntimeError("table 'missing' is not in layer0.tables")

    with pytest.raises(NotFoundError):
        CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="missing", radius=5))


def test_preview_crossmatch_unknown_pgc_column() -> None:
    repo = mock.Mock()
    info = mock.Mock()
    info.columns = {"ra": mock.Mock()}
    repo.get_table_metadata.return_value = info

    with pytest.raises(RuleValidationError):
        CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius=5, pgc_column="pgc"))
    repo.sample_crossmatch_records.assert_not_called()
