import pytest

from app.lib.crossmatch.data import candidates_to_metadata
from app.lib.crossmatch.matching import distribution_key, distribution_rows, results_to_rows
from app.lib.crossmatch.models import (
    CrossmatchResult,
    CrossmatchStatus,
    Neighbor,
    Parameter,
    RecordEvidence,
    TriageStatus,
)
from app.lib.crossmatch.parameters import decide_matched, parameters_payload
from app.lib.crossmatch.resolver import Resolver
from app.lib.storage import enums


@pytest.mark.parametrize(
    ("resolver", "evidence", "status", "triage", "matched_pgc", "colliding_pgcs", "params"),
    [
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(neighbors=[]),
            CrossmatchStatus.NEW,
            TriageStatus.RESOLVED,
            None,
            None,
            {"coordinates": False, "name": False, "nature": False},
        ),
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(
                neighbors=[Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, type_name="G")],
                record_type_name="G",
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.RESOLVED,
            7,
            None,
            {"coordinates": True, "name": False, "nature": True},
        ),
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(neighbors=[Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0)]),
            CrossmatchStatus.EXISTING,
            TriageStatus.PENDING,
            7,
            None,
            {"coordinates": True, "name": False, "nature": False},
        ),
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(
                neighbors=[
                    Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, type_name="G"),
                    Neighbor(pgc=8, ra=10.0, dec=20.0, distance_deg=0.1, type_name="G"),
                ],
                record_type_name="G",
            ),
            CrossmatchStatus.COLLIDING,
            TriageStatus.PENDING,
            None,
            [7, 8],
            None,
        ),
        (
            Resolver(radius_deg=1.0, pgc_column="pgc", include_pgc=True, include_nature=True),
            RecordEvidence(
                neighbors=[
                    Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, type_name="G"),
                    Neighbor(pgc=8, ra=10.0, dec=20.0, distance_deg=0.1, type_name="G"),
                ],
                record_pgc=7,
                claimed_pgc_exists_in_layer2=True,
                record_type_name="G",
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.RESOLVED,
            7,
            None,
            {"coordinates": True, "pgc": True, "nature": True},
        ),
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(
                neighbors=[
                    Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, type_name="G"),
                    Neighbor(pgc=8, ra=10.0, dec=20.0, distance_deg=0.1, type_name="G"),
                ],
                record_designation="NGC 1",
                same_name_pgcs=[7],
                record_type_name="G",
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.RESOLVED,
            7,
            None,
            {"name": True},
        ),
        (
            Resolver(radius_deg=1.0, redshift_tolerance=0.001, include_redshift=True),
            RecordEvidence(
                neighbors=[
                    Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, redshift=0.1),
                    Neighbor(pgc=8, ra=10.0, dec=20.0, distance_deg=0.1, redshift=0.2),
                ],
                record_redshift=0.1005,
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.RESOLVED,
            7,
            None,
            {"coordinates": True, "redshift": True, "name": False},
        ),
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(
                neighbors=[
                    Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, type_name="G"),
                    Neighbor(pgc=8, ra=10.0, dec=20.0, distance_deg=0.1, type_name="Star"),
                ],
                record_type_name="G",
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.RESOLVED,
            7,
            None,
            {"nature": True},
        ),
        (
            Resolver(radius_deg=1.0, pgc_column="pgc", include_pgc=True, include_nature=True),
            RecordEvidence(neighbors=[], record_pgc=9, claimed_pgc_exists_in_layer2=True, record_type_name="G"),
            CrossmatchStatus.EXISTING,
            TriageStatus.PENDING,
            9,
            None,
            {"coordinates": False, "name": False, "pgc": True, "nature": False},
        ),
        (
            Resolver(radius_deg=1.0, pgc_column="pgc", include_pgc=True, include_nature=True),
            RecordEvidence(neighbors=[], record_pgc=9, claimed_pgc_exists_in_layer2=False),
            CrossmatchStatus.NEW,
            TriageStatus.PENDING,
            None,
            None,
            {"pgc": False},
        ),
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(
                neighbors=[],
                record_designation="NGC 1",
                same_name_pgcs=[4],
                record_type_name="G",
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.PENDING,
            4,
            None,
            {"coordinates": False, "name": True},
        ),
        (
            Resolver(radius_deg=1.0, redshift_tolerance=0.001, include_redshift=True, include_nature=True),
            RecordEvidence(
                neighbors=[Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, redshift=0.1, type_name="G")],
                record_redshift=0.2,
                record_type_name="G",
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.RESOLVED,
            7,
            None,
            {"coordinates": True, "redshift": False, "nature": True},
        ),
        (
            Resolver(radius_deg=1.0, include_nature=True),
            RecordEvidence(
                neighbors=[Neighbor(pgc=7, ra=10.0, dec=20.0, distance_deg=0.0, type_name="G")],
                record_type_name="Star",
            ),
            CrossmatchStatus.EXISTING,
            TriageStatus.PENDING,
            7,
            None,
            {"coordinates": True, "nature": False},
        ),
    ],
)
def test_resolver_cases(
    resolver: Resolver,
    evidence: RecordEvidence,
    status: CrossmatchStatus,
    triage: TriageStatus,
    matched_pgc: int | None,
    colliding_pgcs: list[int] | None,
    params: dict[str, bool] | None,
) -> None:
    result = resolver.resolve(evidence)
    assert result.status == status
    assert result.triage_status == triage
    assert result.matched_pgc == matched_pgc
    assert result.colliding_pgcs == colliding_pgcs
    if params is not None:
        for key, value in params.items():
            assert result.parameters[key] is value
    if status == CrossmatchStatus.NEW:
        assert result.candidate_matches == []
    elif matched_pgc is not None:
        assert result.candidate_matches == [(matched_pgc, result.parameters)]
    else:
        assert [pgc for pgc, _matches in result.candidate_matches] == colliding_pgcs
        assert all(matches for _pgc, matches in result.candidate_matches)


@pytest.mark.parametrize(
    ("matches", "expected"),
    [
        ({Parameter.COORDINATES: True, Parameter.NAME: False, Parameter.NATURE: True}, True),
        ({Parameter.COORDINATES: True, Parameter.NAME: True, Parameter.NATURE: False}, True),
        ({Parameter.COORDINATES: True, Parameter.NAME: False, Parameter.NATURE: False}, False),
        ({Parameter.COORDINATES: False, Parameter.NAME: True, Parameter.NATURE: True}, False),
        ({Parameter.COORDINATES: True}, False),
    ],
)
def test_decide_matched(matches: dict[Parameter, bool], expected: bool) -> None:
    assert decide_matched(matches) is expected


def test_results_to_rows_and_distribution() -> None:
    params = {Parameter.COORDINATES: True, Parameter.NAME: False, Parameter.NATURE: True}
    other = {Parameter.COORDINATES: True, Parameter.NAME: False, Parameter.NATURE: False}
    rows = results_to_rows(
        [
            ("a", CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.RESOLVED)),
            (
                "b",
                CrossmatchResult(
                    status=CrossmatchStatus.EXISTING,
                    triage_status=TriageStatus.RESOLVED,
                    matched_pgc=3,
                    parameters=params,
                    candidate_matches=[(3, params)],
                ),
            ),
            (
                "c",
                CrossmatchResult(
                    status=CrossmatchStatus.COLLIDING,
                    triage_status=TriageStatus.PENDING,
                    colliding_pgcs=[8, 2],
                    candidate_matches=[(2, params), (8, other)],
                ),
            ),
        ]
    )
    assert rows == [
        ("a", enums.RecordTriageStatus.RESOLVED, []),
        ("b", enums.RecordTriageStatus.RESOLVED, [(3, params)]),
        ("c", enums.RecordTriageStatus.PENDING, [(2, params), (8, other)]),
    ]
    assert candidates_to_metadata(rows[0][2]) == {}
    assert candidates_to_metadata(rows[1][2]) == {
        "candidates": [{"pgc": 3, "parameters": parameters_payload(params)}],
    }
    assert candidates_to_metadata(rows[2][2]) == {
        "candidates": [
            {"pgc": 2, "parameters": parameters_payload(params)},
            {"pgc": 8, "parameters": parameters_payload(other)},
        ],
    }
    manual = results_to_rows(
        [
            (
                "d",
                CrossmatchResult(
                    status=CrossmatchStatus.EXISTING,
                    triage_status=TriageStatus.RESOLVED,
                    matched_pgc=3,
                    parameters=params,
                ),
            ),
            (
                "e",
                CrossmatchResult(
                    status=CrossmatchStatus.COLLIDING,
                    triage_status=TriageStatus.PENDING,
                    colliding_pgcs=[8, 2],
                ),
            ),
        ]
    )
    assert manual == [
        ("d", enums.RecordTriageStatus.RESOLVED, [3]),
        ("e", enums.RecordTriageStatus.PENDING, [2, 8]),
    ]
    assert candidates_to_metadata([3]) == {"candidates": [{"pgc": 3}]}
    assert candidates_to_metadata([2, 8]) == {"candidates": [{"pgc": 2}, {"pgc": 8}]}
    existing = CrossmatchResult(
        status=CrossmatchStatus.EXISTING,
        triage_status=TriageStatus.RESOLVED,
        matched_pgc=3,
        parameters=params,
    )
    table = distribution_rows(
        {
            distribution_key(
                CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.RESOLVED, parameters={})
            ): 1,
            distribution_key(existing): 4,
        },
        5,
    )
    assert table[0]["status"] == "existing" and table[0]["count"] == 4
    assert table[0]["parameters"] == {"coordinates": True, "name": False, "pgc": None, "redshift": None, "nature": True}
    assert table[1]["percent"] == 20.0
    assert table[1]["parameters"] == {"coordinates": None, "name": None, "pgc": None, "redshift": None, "nature": None}
