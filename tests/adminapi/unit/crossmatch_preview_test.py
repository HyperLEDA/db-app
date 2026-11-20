from unittest import mock

import pytest

from app.adminapi.domain.crossmatch import CrossmatchManager
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi


def _row(rid: str, ra: float, dec: float, *, pgc: int | None = None, design: str | None = None) -> dict:
    return {
        "new_id": rid,
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
    repo.sample_crossmatch_records.return_value = (["near", "far", "hit"], 8, 8)
    repo.fetch_crossmatch_neighbors.return_value = [
        _row("near", 10.0, 20.0, pgc=100, design="NGC 1"),
        _row("far", 180.0, 0.0),
        _row("hit", 11.0, 21.0, pgc=200),
        _row("hit", 11.0, 21.0, pgc=201),
    ]
    repo.pgcs_by_designation.return_value = {"NGC 1": [100]}
    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius_arcsec=30))
    by_status = {s.status: s for s in response.statistics}
    assert (response.total_count, response.eligible_count, response.sample_count) == (8, 8, 3)
    assert set(by_status) == {"existing", "new", "colliding"}
    existing, new, colliding = by_status["existing"], by_status["new"], by_status["colliding"]
    assert existing.triage == "resolved" and existing.count == 1
    assert existing.parameters == adminapi.PreviewCrossmatchParameters(coordinates=True, name=True)
    assert [r.record_id for r in existing.rows] == ["near"]
    assert existing.rows[0].candidates == [100] and existing.rows[0].neighbors[0].pgc == 100
    assert new.triage == "resolved" and [r.record_id for r in new.rows] == ["far"] and new.rows[0].candidates == []
    assert new.parameters == adminapi.PreviewCrossmatchParameters(coordinates=False, name=False)
    assert colliding.triage == "pending" and colliding.count == 1
    assert [r.record_id for r in colliding.rows] == ["hit"] and set(colliding.rows[0].candidates) == {200, 201}
    repo.fetch_claimed_pgcs.assert_not_called()
    repo.sample_crossmatch_records.assert_called_once_with("raw", 1000, None)


def test_preview_crossmatch_uses_sample_size() -> None:
    repo = mock.Mock()
    repo.sample_crossmatch_records.return_value = (["a"], 1, 1)
    repo.fetch_crossmatch_neighbors.return_value = [_row("a", 180.0, 0.0)]
    repo.pgcs_by_designation.return_value = {}
    CrossmatchManager(repo).preview(
        adminapi.PreviewCrossmatchRequest(table_name="raw", radius_arcsec=30, sample_size=250)
    )
    repo.sample_crossmatch_records.assert_called_once_with("raw", 250, None)


def test_preview_crossmatch_returns_subset_of_sample() -> None:
    repo = mock.Mock()
    resolved, pending = [f"r{i}" for i in range(25)], [f"p{i}" for i in range(15)]
    repo.sample_crossmatch_records.return_value = (resolved + pending, 100, 100)
    repo.fetch_crossmatch_neighbors.return_value = [
        *[_row(rid, 180.0, 0.0) for rid in resolved],
        *[row for rid in pending for row in (_row(rid, 10.0, 20.0, pgc=100), _row(rid, 10.0, 20.0, pgc=101))],
    ]
    repo.pgcs_by_designation.return_value = {}
    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius_arcsec=30))
    by_status = {s.status: s for s in response.statistics}
    assert response.sample_count == 40 and set(by_status) == {"new", "colliding"}
    assert by_status["new"].count == 25 and by_status["new"].percent == 62.5
    assert by_status["colliding"].count == 15 and by_status["colliding"].percent == 37.5
    assert len(by_status["new"].rows) == len(by_status["colliding"].rows) == 10
    assert {r.record_id for r in by_status["new"].rows} <= set(resolved)
    assert {r.record_id for r in by_status["colliding"].rows} <= set(pending)
    assert by_status["new"].triage == "resolved" and by_status["colliding"].triage == "pending"


def test_preview_crossmatch_missing_table() -> None:
    repo = mock.Mock()
    repo.sample_crossmatch_records.side_effect = RuntimeError("table 'missing' is not in layer0.tables")
    with pytest.raises(NotFoundError):
        CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="missing", radius_arcsec=5))


def test_preview_crossmatch_unknown_pgc_column() -> None:
    repo = mock.Mock()
    info = mock.Mock()
    info.columns = {"ra": mock.Mock()}
    repo.get_table_metadata.return_value = info
    with pytest.raises(RuleValidationError):
        CrossmatchManager(repo).preview(
            adminapi.PreviewCrossmatchRequest(table_name="raw", radius_arcsec=5, pgc_column="pgc")
        )
    repo.sample_crossmatch_records.assert_not_called()
