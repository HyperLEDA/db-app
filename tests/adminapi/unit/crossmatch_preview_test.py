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
    repo.sample_crossmatch_records.return_value = (["near", "far", "hit"], 8, 8)
    repo.fetch_crossmatch_neighbors.return_value = [
        _row("near", 10.0, 20.0, pgc=100, design="NGC 1"),
        _row("far", 180.0, 0.0),
        _row("hit", 11.0, 21.0, pgc=200),
        _row("hit", 11.0, 21.0, pgc=201),
    ]
    repo.pgcs_by_designation.return_value = {"NGC 1": [100]}

    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius_arcsec=30))

    by_status = {stat.status: stat for stat in response.statistics}
    assert response.total_count == 8
    assert response.eligible_count == 8
    assert response.sample_count == 3
    assert set(by_status) == {"existing", "new", "colliding"}

    existing = by_status["existing"]
    assert existing.triage == "resolved"
    assert existing.count == 1
    assert existing.parameters == adminapi.PreviewCrossmatchParameters(coordinates=True, name=True)
    assert [row.record_id for row in existing.rows] == ["near"]
    assert existing.rows[0].candidates == [100]
    assert existing.rows[0].neighbors[0].pgc == 100

    new = by_status["new"]
    assert new.triage == "resolved"
    assert [row.record_id for row in new.rows] == ["far"]
    assert new.rows[0].candidates == []
    assert new.parameters == adminapi.PreviewCrossmatchParameters(coordinates=False, name=False)

    colliding = by_status["colliding"]
    assert colliding.triage == "pending"
    assert colliding.count == 1
    assert [row.record_id for row in colliding.rows] == ["hit"]
    assert set(colliding.rows[0].candidates) == {200, 201}
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
    resolved_ids = [f"r{i}" for i in range(25)]
    pending_ids = [f"p{i}" for i in range(15)]
    record_ids = resolved_ids + pending_ids
    repo.sample_crossmatch_records.return_value = (record_ids, 100, 100)
    repo.fetch_crossmatch_neighbors.return_value = [
        *[_row(record_id, 180.0, 0.0) for record_id in resolved_ids],
        *[
            row
            for record_id in pending_ids
            for row in (
                _row(record_id, 10.0, 20.0, pgc=100),
                _row(record_id, 10.0, 20.0, pgc=101),
            )
        ],
    ]
    repo.pgcs_by_designation.return_value = {}

    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius_arcsec=30))

    assert response.sample_count == 40
    by_status = {stat.status: stat for stat in response.statistics}
    assert set(by_status) == {"new", "colliding"}
    assert by_status["new"].count == 25 and by_status["new"].percent == 62.5
    assert by_status["colliding"].count == 15 and by_status["colliding"].percent == 37.5
    assert len(by_status["new"].rows) == 10
    assert len(by_status["colliding"].rows) == 10
    assert {row.record_id for row in by_status["new"].rows} <= set(resolved_ids)
    assert {row.record_id for row in by_status["colliding"].rows} <= set(pending_ids)
    assert by_status["new"].triage == "resolved"
    assert by_status["colliding"].triage == "pending"


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
            adminapi.PreviewCrossmatchRequest(
                table_name="raw",
                radius_arcsec=5,
                pgc_column="pgc",
            )
        )
    repo.sample_crossmatch_records.assert_not_called()
