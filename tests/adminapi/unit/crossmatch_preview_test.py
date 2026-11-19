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

    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius=30))

    pending_by_id = {row.record_id: row for row in response.pending_rows}
    resolved_by_id = {row.record_id: row for row in response.resolved_rows}
    assert response.total_count == 8
    assert response.eligible_count == 8
    assert response.sample_count == 3
    assert set(pending_by_id) == {"hit"}
    assert set(resolved_by_id) == {"near", "far"}
    assert pending_by_id["hit"].status == "colliding"
    assert pending_by_id["hit"].triage == "pending"
    assert set(pending_by_id["hit"].candidates) == {200, 201}
    assert resolved_by_id["near"].status == "existing"
    assert resolved_by_id["near"].triage == "resolved"
    assert resolved_by_id["near"].parameters == adminapi.PreviewCrossmatchParameters(
        coordinates=True,
        name=True,
    )
    assert resolved_by_id["near"].candidates == [100] and resolved_by_id["near"].neighbors[0].pgc == 100
    assert resolved_by_id["far"].status == "new" and resolved_by_id["far"].candidates == []
    assert resolved_by_id["far"].parameters == adminapi.PreviewCrossmatchParameters(
        coordinates=False,
        name=False,
    )
    existing_stat = next(stat for stat in response.statistics if stat.status == "existing")
    assert existing_stat.parameters == adminapi.PreviewCrossmatchParameters(
        coordinates=True,
        name=True,
    )
    colliding_stat = next(stat for stat in response.statistics if stat.status == "colliding")
    assert colliding_stat.triage == "pending"
    assert colliding_stat.count == 1
    repo.fetch_claimed_pgcs.assert_not_called()
    repo.sample_crossmatch_records.assert_called_once_with("raw", 1000, None)


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

    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name="raw", radius=30))

    assert response.sample_count == 40
    assert len(response.pending_rows) == 10
    assert len(response.resolved_rows) == 10
    assert {row.record_id for row in response.pending_rows} <= set(pending_ids)
    assert {row.record_id for row in response.resolved_rows} <= set(resolved_ids)
    assert all(row.triage == "pending" for row in response.pending_rows)
    assert all(row.triage == "resolved" for row in response.resolved_rows)
    assert {(stat.status, stat.triage, stat.count, stat.percent) for stat in response.statistics} == {
        ("new", "resolved", 25, 62.5),
        ("colliding", "pending", 15, 37.5),
    }


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
        CrossmatchManager(repo).preview(
            adminapi.PreviewCrossmatchRequest(
                table_name="raw",
                radius=5,
                include_pgc=True,
                pgc_column="pgc",
            )
        )
    repo.sample_crossmatch_records.assert_not_called()
