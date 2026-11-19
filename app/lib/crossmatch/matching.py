import math
from collections.abc import Mapping, Sequence
from typing import Any

from app.lib.crossmatch.models import (
    CrossmatchResult,
    CrossmatchStatus,
    MatchedRecord,
    Neighbor,
    Parameter,
    RecordEvidence,
    TriageStatus,
)
from app.lib.crossmatch.parameters import parameters_payload
from app.lib.crossmatch.resolver import Resolver
from app.lib.storage import enums

C_M_S = 299792458

DistributionKey = tuple[CrossmatchStatus, TriageStatus, tuple[tuple[Parameter, bool], ...]]


def distribution_key(result: CrossmatchResult) -> DistributionKey:
    return (result.status, result.triage_status, tuple(result.parameters.items()))


def distribution_rows(
    counts: Mapping[DistributionKey, int],
    total: int,
) -> list[dict[str, Any]]:
    def pct(n: int) -> float:
        return round((100.0 * n / total) if total else 0.0, 1)

    ordered = sorted(
        counts,
        key=lambda key: (-counts[key], key[0].value, key[1].value, tuple(key[2])),
    )
    return [
        {
            "status": status.value,
            "triage": triage.value,
            "parameters": parameters_payload(dict(parameter_items)),
            "count": counts[(status, triage, parameter_items)],
            "percent": pct(counts[(status, triage, parameter_items)]),
        }
        for status, triage, parameter_items in ordered
        if counts[(status, triage, parameter_items)] > 0
    ]


def results_to_rows(
    results: Sequence[tuple[str, CrossmatchResult]],
) -> list[tuple[str, enums.RecordTriageStatus, list[int]]]:
    rows: list[tuple[str, enums.RecordTriageStatus, list[int]]] = []
    for record_id, result in results:
        triage = enums.RecordTriageStatus(result.triage_status.value)
        if result.status == CrossmatchStatus.NEW:
            rows.append((record_id, triage, []))
        elif result.status == CrossmatchStatus.EXISTING and result.matched_pgc is not None:
            rows.append((record_id, triage, [result.matched_pgc]))
        elif result.status == CrossmatchStatus.COLLIDING and result.colliding_pgcs:
            rows.append((record_id, triage, sorted(result.colliding_pgcs)))
    return rows


def angular_distance_deg(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    d_dec = dec1 - dec2
    d_ra = (ra1 - ra2) * math.cos(math.radians((dec1 + dec2) / 2))
    return math.sqrt(d_dec**2 + d_ra**2)


def group_batch(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], str]:
    by_record: dict[str, dict[str, Any]] = {}
    last_id = ""
    for row in rows:
        new_id = str(row["new_id"])
        last_id = new_id
        if new_id not in by_record:
            by_record[new_id] = {
                "new_ra": None,
                "new_dec": None,
                "new_design": None,
                "new_redshift": None,
                "new_type": None,
                "candidates": [],
            }
        rec = by_record[new_id]
        if row["new_ra"] is not None:
            rec["new_ra"] = row["new_ra"]
            rec["new_dec"] = row["new_dec"]
        if row["new_design"] is not None:
            rec["new_design"] = row["new_design"]
        if row["new_cz"] is not None:
            rec["new_redshift"] = float(row["new_cz"]) / C_M_S
        if row.get("new_type") is not None:
            rec["new_type"] = row["new_type"]
        if row["existing_pgc"] is not None and row["existing_ra"] is not None and row["existing_dec"] is not None:
            existing_redshift = float(row["existing_cz"]) / C_M_S if row["existing_cz"] is not None else None
            rec["candidates"].append(
                (
                    row["existing_ra"],
                    row["existing_dec"],
                    int(row["existing_pgc"]),
                    row["existing_design"],
                    existing_redshift,
                    row.get("existing_type"),
                )
            )
    return by_record, last_id


def resolve_batch(
    by_record: Mapping[str, Mapping[str, Any]],
    record_pgc_by_id: Mapping[str, int | None],
    existing_pgcs: set[int],
    design_to_pgcs: Mapping[str, list[int]],
    resolver: Resolver,
) -> list[MatchedRecord]:
    matched: list[MatchedRecord] = []
    radius_deg = resolver.search_radius_deg
    for record_id, rec_data in by_record.items():
        neighbors: list[Neighbor] = []
        new_ra = rec_data["new_ra"]
        new_dec = rec_data["new_dec"]
        if new_ra is not None and new_dec is not None:
            for existing_ra, existing_dec, pgc, existing_design, existing_redshift, existing_type in rec_data[
                "candidates"
            ]:
                dist = angular_distance_deg(float(new_ra), float(new_dec), float(existing_ra), float(existing_dec))
                if dist <= radius_deg:
                    neighbors.append(
                        Neighbor(
                            pgc=pgc,
                            ra=float(existing_ra),
                            dec=float(existing_dec),
                            distance_deg=dist,
                            design=existing_design,
                            redshift=existing_redshift,
                            type_name=existing_type,
                        )
                    )
        record_designation = rec_data["new_design"]
        record_pgc = record_pgc_by_id.get(record_id) if record_pgc_by_id else None
        evidence = RecordEvidence(
            neighbors=neighbors,
            record_designation=record_designation,
            same_name_pgcs=design_to_pgcs.get(record_designation, []) if record_designation is not None else None,
            record_pgc=record_pgc,
            claimed_pgc_exists_in_layer2=record_pgc is not None and record_pgc in existing_pgcs,
            record_redshift=rec_data.get("new_redshift"),
            record_type_name=rec_data.get("new_type"),
        )
        result = resolver.resolve(evidence)
        matched.append(
            MatchedRecord(
                record_id=record_id,
                result=result,
                designation=record_designation,
                ra=float(new_ra) if new_ra is not None else None,
                dec=float(new_dec) if new_dec is not None else None,
                neighbors=neighbors,
            )
        )
    return matched


def match_records(
    rows: Sequence[Mapping[str, Any]],
    *,
    radius_deg: float,
    pgc_column: str | None,
    redshift_tolerance: float | None,
    record_pgc_by_id: Mapping[str, int | None],
    existing_pgcs: set[int],
    design_to_pgcs: Mapping[str, list[int]],
    include_pgc: bool = False,
    include_redshift: bool = False,
    include_nature: bool = False,
) -> list[MatchedRecord]:
    by_record, _last_id = group_batch(rows)
    resolver = Resolver(
        radius_deg=radius_deg,
        pgc_column=pgc_column,
        redshift_tolerance=redshift_tolerance,
        include_pgc=include_pgc,
        include_redshift=include_redshift,
        include_nature=include_nature,
    )
    return resolve_batch(by_record, record_pgc_by_id, existing_pgcs, design_to_pgcs, resolver)
