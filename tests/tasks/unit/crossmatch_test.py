from app.lib.crossmatch.matching import distribution_key, distribution_rows, results_to_rows
from app.lib.crossmatch.models import (
    CrossmatchResult,
    CrossmatchStatus,
    Neighbor,
    Parameter,
    RecordEvidence,
    TriageStatus,
)
from app.lib.crossmatch.parameters import decide_matched
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
    resolver = Resolver(radius_deg=1.0, include_nature=True)
    new = resolver.resolve(_evidence())
    assert new.status == CrossmatchStatus.NEW and new.triage_status == TriageStatus.RESOLVED
    assert new.parameters == {"coordinates": False, "name": False, "type": False}

    existing = resolver.resolve(_evidence(neighbors=[_neighbor(7, type_name="G")], record_type_name="G"))
    assert existing.status == CrossmatchStatus.EXISTING
    assert existing.triage_status == TriageStatus.RESOLVED
    assert existing.matched_pgc == 7
    assert existing.parameters == {"coordinates": True, "name": False, "type": True}

    missing_type = resolver.resolve(_evidence(neighbors=[_neighbor(7)]))
    assert missing_type.status == CrossmatchStatus.EXISTING
    assert missing_type.triage_status == TriageStatus.PENDING
    assert missing_type.parameters == {"coordinates": True, "name": False, "type": False}

    colliding = resolver.resolve(
        _evidence(
            neighbors=[
                _neighbor(7, type_name="G"),
                _neighbor(8, distance_deg=0.1, type_name="G"),
            ],
            record_type_name="G",
        )
    )
    assert colliding.status == CrossmatchStatus.COLLIDING
    assert colliding.triage_status == TriageStatus.PENDING
    assert colliding.colliding_pgcs == [7, 8]


def test_resolver_matched_by_identifier_and_filters() -> None:
    by_pgc = Resolver(radius_deg=1.0, pgc_column="pgc", include_pgc=True, include_nature=True).resolve(
        _evidence(
            neighbors=[
                _neighbor(7, type_name="G"),
                _neighbor(8, distance_deg=0.1, type_name="G"),
            ],
            record_pgc=7,
            claimed_pgc_exists_in_layer2=True,
            record_type_name="G",
        )
    )
    assert by_pgc.status == CrossmatchStatus.EXISTING
    assert by_pgc.triage_status == TriageStatus.RESOLVED
    assert by_pgc.matched_pgc == 7
    assert by_pgc.parameters["coordinates"] is True
    assert by_pgc.parameters["pgc"] is True
    assert by_pgc.parameters["type"] is True

    by_name = Resolver(radius_deg=1.0, include_nature=True).resolve(
        _evidence(
            neighbors=[
                _neighbor(7, type_name="G"),
                _neighbor(8, distance_deg=0.1, type_name="G"),
            ],
            record_designation="NGC 1",
            same_name_pgcs=[7],
            record_type_name="G",
        )
    )
    assert by_name.status == CrossmatchStatus.EXISTING
    assert by_name.triage_status == TriageStatus.RESOLVED
    assert by_name.matched_pgc == 7
    assert by_name.parameters["name"] is True

    by_redshift = Resolver(radius_deg=1.0, redshift_tolerance=0.001, include_redshift=True).resolve(
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
    assert by_redshift.parameters["coordinates"] is True
    assert by_redshift.parameters["redshift"] is True
    assert by_redshift.parameters["name"] is False

    by_type = Resolver(radius_deg=1.0, include_nature=True).resolve(
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
    assert by_type.parameters["type"] is True


def test_resolver_pgc_name_redshift_and_type() -> None:
    outside = Resolver(radius_deg=1.0, pgc_column="pgc", include_pgc=True, include_nature=True).resolve(
        _evidence(record_pgc=9, claimed_pgc_exists_in_layer2=True, record_type_name="G")
    )
    assert outside.status == CrossmatchStatus.EXISTING
    assert outside.triage_status == TriageStatus.PENDING
    assert outside.matched_pgc == 9
    assert outside.parameters == {
        "coordinates": False,
        "name": False,
        "pgc": True,
        "type": False,
    }

    unknown = Resolver(radius_deg=1.0, pgc_column="pgc", include_pgc=True, include_nature=True).resolve(
        _evidence(record_pgc=9, claimed_pgc_exists_in_layer2=False)
    )
    assert unknown.status == CrossmatchStatus.NEW
    assert unknown.triage_status == TriageStatus.PENDING
    assert unknown.parameters["pgc"] is False

    named = Resolver(radius_deg=1.0, include_nature=True).resolve(
        _evidence(record_designation="NGC 1", same_name_pgcs=[4], record_type_name="G")
    )
    assert named.status == CrossmatchStatus.EXISTING
    assert named.triage_status == TriageStatus.PENDING
    assert named.matched_pgc == 4
    assert named.parameters["coordinates"] is False
    assert named.parameters["name"] is True

    redshift = Resolver(radius_deg=1.0, redshift_tolerance=0.001, include_redshift=True, include_nature=True).resolve(
        _evidence(
            neighbors=[_neighbor(7, redshift=0.1, type_name="G")],
            record_redshift=0.2,
            record_type_name="G",
        )
    )
    assert redshift.status == CrossmatchStatus.EXISTING
    assert redshift.triage_status == TriageStatus.RESOLVED
    assert redshift.matched_pgc == 7
    assert redshift.parameters["coordinates"] is True
    assert redshift.parameters["redshift"] is False
    assert redshift.parameters["type"] is True

    typed = Resolver(radius_deg=1.0, include_nature=True).resolve(
        _evidence(neighbors=[_neighbor(7, type_name="G")], record_type_name="Star")
    )
    assert typed.status == CrossmatchStatus.EXISTING
    assert typed.triage_status == TriageStatus.PENDING
    assert typed.parameters["coordinates"] is True
    assert typed.parameters["type"] is False


def test_decide_matched() -> None:
    assert decide_matched({Parameter.COORDINATES: True, Parameter.NAME: False, Parameter.TYPE: True})
    assert decide_matched({Parameter.COORDINATES: True, Parameter.NAME: True, Parameter.TYPE: False})
    assert not decide_matched({Parameter.COORDINATES: True, Parameter.NAME: False, Parameter.TYPE: False})
    assert not decide_matched({Parameter.COORDINATES: False, Parameter.NAME: True, Parameter.TYPE: True})
    assert not decide_matched({Parameter.COORDINATES: True})


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
                    parameters={
                        Parameter.COORDINATES: True,
                        Parameter.NAME: False,
                        Parameter.TYPE: True,
                    },
                ),
            ),
            (
                "c",
                CrossmatchResult(
                    status=CrossmatchStatus.COLLIDING,
                    triage_status=TriageStatus.PENDING,
                    colliding_pgcs=[8, 2],
                ),
            ),
        ]
    )
    assert rows == [
        ("a", enums.RecordTriageStatus.RESOLVED, []),
        ("b", enums.RecordTriageStatus.RESOLVED, [3]),
        ("c", enums.RecordTriageStatus.PENDING, [2, 8]),
    ]
    existing = CrossmatchResult(
        status=CrossmatchStatus.EXISTING,
        triage_status=TriageStatus.RESOLVED,
        matched_pgc=3,
        parameters={
            Parameter.COORDINATES: True,
            Parameter.NAME: False,
            Parameter.TYPE: True,
        },
    )
    new = CrossmatchResult(status=CrossmatchStatus.NEW, triage_status=TriageStatus.RESOLVED, parameters={})
    table = distribution_rows(
        {
            distribution_key(new): 1,
            distribution_key(existing): 4,
        },
        5,
    )
    assert table[0]["status"] == "existing" and table[0]["count"] == 4
    assert table[0]["parameters"] == {
        "coordinates": True,
        "name": False,
        "pgc": None,
        "redshift": None,
        "type": True,
    }
    assert table[1]["percent"] == 20.0
    assert table[1]["parameters"] == {
        "coordinates": None,
        "name": None,
        "pgc": None,
        "redshift": None,
        "type": None,
    }
