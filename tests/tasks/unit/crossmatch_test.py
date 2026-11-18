from app.lib.storage import enums
from app.tasks.crossmatch.engine import distribution_rows, results_to_rows
from app.tasks.crossmatch.models import (
    CrossmatchResult,
    CrossmatchStatus,
    Neighbor,
    PendingReason,
    RecordEvidence,
    TriageStatus,
)
from app.tasks.crossmatch.resolver import Resolver


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

    existing = resolver.resolve(_evidence(neighbors=[_neighbor(7)]))
    assert existing.status == CrossmatchStatus.EXISTING
    assert existing.triage_status == TriageStatus.RESOLVED
    assert existing.matched_pgc == 7

    colliding = resolver.resolve(_evidence(neighbors=[_neighbor(7), _neighbor(8, distance_deg=0.1)]))
    assert colliding.status == CrossmatchStatus.COLLIDING
    assert colliding.triage_status == TriageStatus.PENDING
    assert colliding.pending_reason == PendingReason.MULTIPLE_OBJECTS_MATCHED


def test_resolver_pgc_name_redshift_and_type() -> None:
    outside = Resolver(radius_deg=1.0, pgc_column="pgc").resolve(
        _evidence(record_pgc=9, claimed_pgc_exists_in_layer2=True)
    )
    assert outside.pending_reason == PendingReason.MATCHED_PGC_OUTSIDE_CIRCLE
    assert outside.matched_pgc == 9

    unknown = Resolver(radius_deg=1.0, pgc_column="pgc").resolve(
        _evidence(record_pgc=9, claimed_pgc_exists_in_layer2=False)
    )
    assert unknown.pending_reason == PendingReason.UNKNOWN_PGC

    named = Resolver(radius_deg=1.0).resolve(_evidence(record_designation="NGC 1", same_name_pgcs=[4]))
    assert named.pending_reason == PendingReason.MATCHED_NAME_OUTSIDE_CIRCLE
    assert named.matched_pgc == 4

    redshift = Resolver(radius_deg=1.0, redshift_tolerance=0.001).resolve(
        _evidence(neighbors=[_neighbor(7, redshift=0.1)], record_redshift=0.2)
    )
    assert redshift.pending_reason == PendingReason.REDSHIFT_MISMATCH
    assert redshift.matched_pgc == 7

    typed = Resolver(radius_deg=1.0).resolve(
        _evidence(neighbors=[_neighbor(7, type_name="G")], record_type_name="Star")
    )
    assert typed.pending_reason == PendingReason.TYPE_MISMATCH


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
                    pending_reason=PendingReason.MULTIPLE_OBJECTS_MATCHED,
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
