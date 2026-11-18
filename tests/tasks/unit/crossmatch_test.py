from app.lib.crossmatch.matching import distribution_rows, results_to_rows
from app.lib.crossmatch.models import (
    CrossmatchReason,
    CrossmatchResult,
    CrossmatchStatus,
    Neighbor,
    RecordEvidence,
    TriageStatus,
)
from app.lib.crossmatch.resolver import Resolver
from app.lib.storage import enums


def _neighbor(
    pgc: int,
    distance_deg: float = 0.0,
    redshift: float | None = None,
    type_name: str | None = None,
) -> Neighbor:
    return Neighbor(pgc=pgc, ra=10.0, dec=20.0, distance_deg=distance_deg, redshift=redshift, type_name=type_name)


def _evidence(
    neighbors: list[Neighbor] | None = None,
    record_designation: str | None = None,
    same_name_pgcs: list[int] | None = None,
    record_pgc: int | None = None,
    claimed_pgc_exists_in_layer2: bool = False,
    record_redshift: float | None = None,
    record_type_name: str | None = None,
) -> RecordEvidence:
    return RecordEvidence(
        neighbors=neighbors or [],
        record_designation=record_designation,
        same_name_pgcs=same_name_pgcs,
        record_pgc=record_pgc,
        claimed_pgc_exists_in_layer2=claimed_pgc_exists_in_layer2,
        record_redshift=record_redshift,
        record_type_name=record_type_name,
    )


def test_resolver_new_and_existing() -> None:
    resolver = Resolver(radius_deg=1.0)
    new = resolver.resolve(_evidence())
    assert new.status == CrossmatchStatus.NEW and new.triage_status == TriageStatus.RESOLVED
    assert new.reason is None

    existing = resolver.resolve(_evidence(neighbors=[_neighbor(7)]))
    assert existing.status == CrossmatchStatus.EXISTING
    assert existing.triage_status == TriageStatus.RESOLVED
    assert existing.matched_pgc == 7
    assert existing.reason == CrossmatchReason.MATCHED_COORDINATES

    colliding = resolver.resolve(_evidence(neighbors=[_neighbor(7), _neighbor(8, distance_deg=0.1)]))
    assert colliding.status == CrossmatchStatus.COLLIDING
    assert colliding.triage_status == TriageStatus.PENDING
    assert colliding.reason == CrossmatchReason.MULTIPLE_OBJECTS_MATCHED


def test_resolver_matched_by_first_narrowing_rule() -> None:
    by_pgc = Resolver(radius_deg=1.0, pgc_column="pgc").resolve(
        _evidence(
            neighbors=[_neighbor(7), _neighbor(8, distance_deg=0.1)],
            record_pgc=7,
            claimed_pgc_exists_in_layer2=True,
        )
    )
    assert by_pgc.status == CrossmatchStatus.EXISTING
    assert by_pgc.triage_status == TriageStatus.RESOLVED
    assert by_pgc.matched_pgc == 7
    assert by_pgc.reason == CrossmatchReason.MATCHED_PGC

    by_name = Resolver(radius_deg=1.0).resolve(
        _evidence(
            neighbors=[_neighbor(7), _neighbor(8, distance_deg=0.1)],
            record_designation="NGC 1",
            same_name_pgcs=[7],
        )
    )
    assert by_name.status == CrossmatchStatus.EXISTING
    assert by_name.triage_status == TriageStatus.RESOLVED
    assert by_name.matched_pgc == 7
    assert by_name.reason == CrossmatchReason.MATCHED_NAME

    by_redshift = Resolver(radius_deg=1.0, redshift_tolerance=0.001).resolve(
        _evidence(
            neighbors=[
                _neighbor(7, redshift=0.1),
                _neighbor(8, distance_deg=0.1, redshift=0.2),
            ],
            record_redshift=0.1005,
        )
    )
    assert by_redshift.status == CrossmatchStatus.EXISTING
    assert by_redshift.triage_status == TriageStatus.RESOLVED
    assert by_redshift.matched_pgc == 7
    assert by_redshift.reason == CrossmatchReason.MATCHED_REDSHIFT

    by_type = Resolver(radius_deg=1.0).resolve(
        _evidence(
            neighbors=[
                _neighbor(7, type_name="G"),
                _neighbor(8, distance_deg=0.1, type_name="Star"),
            ],
            record_type_name="G",
        )
    )
    assert by_type.status == CrossmatchStatus.EXISTING
    assert by_type.triage_status == TriageStatus.RESOLVED
    assert by_type.matched_pgc == 7
    assert by_type.reason == CrossmatchReason.MATCHED_TYPE

    first_wins = Resolver(radius_deg=1.0, pgc_column="pgc", redshift_tolerance=0.001).resolve(
        _evidence(
            neighbors=[
                _neighbor(7, redshift=0.1, type_name="G"),
                _neighbor(8, distance_deg=0.1, redshift=0.2, type_name="Star"),
            ],
            record_pgc=7,
            claimed_pgc_exists_in_layer2=True,
            record_designation="NGC 1",
            same_name_pgcs=[7],
            record_redshift=0.1005,
            record_type_name="G",
        )
    )
    assert first_wins.reason == CrossmatchReason.MATCHED_PGC
    assert first_wins.matched_pgc == 7


def test_resolver_pgc_name_redshift_and_type() -> None:
    outside = Resolver(radius_deg=1.0, pgc_column="pgc").resolve(
        _evidence(record_pgc=9, claimed_pgc_exists_in_layer2=True)
    )
    assert outside.reason == CrossmatchReason.MATCHED_PGC_OUTSIDE_CIRCLE
    assert outside.matched_pgc == 9

    unknown = Resolver(radius_deg=1.0, pgc_column="pgc").resolve(
        _evidence(record_pgc=9, claimed_pgc_exists_in_layer2=False)
    )
    assert unknown.reason == CrossmatchReason.UNKNOWN_PGC

    named = Resolver(radius_deg=1.0).resolve(_evidence(record_designation="NGC 1", same_name_pgcs=[4]))
    assert named.reason == CrossmatchReason.MATCHED_NAME_OUTSIDE_CIRCLE
    assert named.matched_pgc == 4

    redshift = Resolver(radius_deg=1.0, redshift_tolerance=0.001).resolve(
        _evidence(neighbors=[_neighbor(7, redshift=0.1)], record_redshift=0.2)
    )
    assert redshift.reason == CrossmatchReason.REDSHIFT_MISMATCH
    assert redshift.matched_pgc == 7

    typed = Resolver(radius_deg=1.0).resolve(
        _evidence(neighbors=[_neighbor(7, type_name="G")], record_type_name="Star")
    )
    assert typed.reason == CrossmatchReason.TYPE_MISMATCH


def test_results_to_rows_and_distribution() -> None:
    rows = results_to_rows(
        [
            ("a", CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.RESOLVED)),
            (
                "b",
                CrossmatchResult(
                    status=CrossmatchStatus.EXISTING,
                    triage_status=TriageStatus.RESOLVED,
                    matched_pgc=3,
                ),
            ),
            (
                "c",
                CrossmatchResult(
                    status=CrossmatchStatus.COLLIDING,
                    triage_status=TriageStatus.PENDING,
                    colliding_pgcs=[8, 2],
                    reason=CrossmatchReason.MULTIPLE_OBJECTS_MATCHED,
                ),
            ),
        ]
    )
    assert rows == [
        ("a", enums.RecordTriageStatus.RESOLVED, []),
        ("b", enums.RecordTriageStatus.RESOLVED, [3]),
        ("c", enums.RecordTriageStatus.PENDING, [2, 8]),
    ]
    table = distribution_rows(
        {
            (CrossmatchStatus.NEW, TriageStatus.RESOLVED, None): 1,
            (CrossmatchStatus.EXISTING, TriageStatus.RESOLVED, None): 4,
        },
        5,
    )
    assert table[0]["status"] == "existing" and table[0]["count"] == 4
    assert table[1]["percent"] == 20.0
