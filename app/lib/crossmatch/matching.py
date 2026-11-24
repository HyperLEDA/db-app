import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from app.lib.crossmatch.models import (
    CrossmatchResult,
    CrossmatchStatus,
    MatchedRecord,
    Neighbor,
    Parameter,
    ParameterMatches,
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


def ordered_distribution_keys(counts: Mapping[DistributionKey, int]) -> list[DistributionKey]:
    return sorted(counts, key=lambda key: (-counts[key], key[0].value, key[1].value, tuple(key[2])))


def distribution_rows(counts: Mapping[DistributionKey, int], total: int) -> list[dict[str, Any]]:
    return [
        {
            "status": status.value,
            "triage": triage.value,
            "parameters": parameters_payload(dict(parameter_items)),
            "count": n,
            "percent": round((100.0 * n / total) if total else 0.0, 1),
        }
        for status, triage, parameter_items in ordered_distribution_keys(counts)
        if (n := counts[(status, triage, parameter_items)]) > 0
    ]


def candidate_pgcs(candidates: Sequence[int | tuple[int, ParameterMatches]]) -> list[int]:
    return [candidate if isinstance(candidate, int) else candidate[0] for candidate in candidates]


def results_to_rows(
    results: Sequence[tuple[str, CrossmatchResult]],
) -> list[tuple[str, enums.RecordTriageStatus, list[int] | list[tuple[int, ParameterMatches]]]]:
    rows: list[tuple[str, enums.RecordTriageStatus, list[int] | list[tuple[int, ParameterMatches]]]] = []
    for record_id, result in results:
        triage = enums.RecordTriageStatus(result.triage_status.value)
        candidates = _row_candidates(result)
        if result.status == CrossmatchStatus.NEW:
            rows.append((record_id, triage, candidates))
        elif result.status == CrossmatchStatus.EXISTING and result.matched_pgc is not None:
            rows.append((record_id, triage, candidates))
        elif result.status == CrossmatchStatus.COLLIDING and result.colliding_pgcs:
            rows.append((record_id, triage, candidates))
    return rows


def _row_candidates(result: CrossmatchResult) -> list[int] | list[tuple[int, ParameterMatches]]:
    if result.candidate_matches:
        return [(pgc, dict(matches)) for pgc, matches in result.candidate_matches]
    if result.status == CrossmatchStatus.EXISTING and result.matched_pgc is not None:
        return [result.matched_pgc]
    if result.status == CrossmatchStatus.COLLIDING and result.colliding_pgcs:
        return sorted(result.colliding_pgcs)
    return []


def angular_distance_deg(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    d_dec = dec1 - dec2
    d_ra = (ra1 - ra2) * math.cos(math.radians((dec1 + dec2) / 2))
    return math.sqrt(d_dec**2 + d_ra**2)


def _candidates(row: Mapping[str, Any]) -> list[tuple[Any, ...]]:
    if row["neighbor_pgcs"] is None:
        return []
    return [
        (ra, dec, int(pgc), design, float(cz) / C_M_S if cz is not None else None, type_name)
        for pgc, ra, dec, design, type_name, cz in zip(
            row["neighbor_pgcs"],
            row["neighbor_ras"],
            row["neighbor_decs"],
            row["neighbor_designs"],
            row["neighbor_types"],
            row["neighbor_czs"],
            strict=True,
        )
    ]


def group_inputs(inputs: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row["id"]): {
            "new_ra": row["ra"],
            "new_dec": row["dec"],
            "new_design": row["design"],
            "new_redshift": float(row["cz"]) / C_M_S if row["cz"] is not None else None,
            "new_type": row["type_name"],
            "candidates": _candidates(row),
        }
        for row in inputs
    }


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
        new_ra, new_dec = rec_data["new_ra"], rec_data["new_dec"]
        neighbors: list[Neighbor] = []
        if new_ra is not None and new_dec is not None:
            for existing_ra, existing_dec, pgc, design, redshift, type_name in rec_data["candidates"]:
                dist = angular_distance_deg(float(new_ra), float(new_dec), float(existing_ra), float(existing_dec))
                if dist <= radius_deg:
                    neighbors.append(
                        Neighbor(
                            pgc=pgc,
                            ra=float(existing_ra),
                            dec=float(existing_dec),
                            distance_deg=dist,
                            design=design,
                            redshift=redshift,
                            type_name=type_name,
                        )
                    )
        designation = rec_data["new_design"]
        record_pgc = record_pgc_by_id.get(record_id) if record_pgc_by_id else None
        matched.append(
            MatchedRecord(
                record_id=record_id,
                result=resolver.resolve(
                    RecordEvidence(
                        neighbors=neighbors,
                        record_designation=designation,
                        same_name_pgcs=design_to_pgcs.get(designation, []) if designation is not None else None,
                        record_pgc=record_pgc,
                        claimed_pgc_exists_in_layer2=record_pgc is not None and record_pgc in existing_pgcs,
                        record_redshift=rec_data.get("new_redshift"),
                        record_type_name=rec_data.get("new_type"),
                    )
                ),
                designation=designation,
                ra=float(new_ra) if new_ra is not None else None,
                dec=float(new_dec) if new_dec is not None else None,
                neighbors=neighbors,
            )
        )
    return matched


def resolve_inputs(
    inputs: Sequence[Mapping[str, Any]],
    resolver: Resolver,
    layer2_pgcs: Callable[[list[int]], set[int]],
) -> list[MatchedRecord]:
    record_pgc_by_id = (
        {str(row["id"]): int(row["claimed_pgc"]) if row["claimed_pgc"] is not None else None for row in inputs}
        if resolver.pgc_column is not None
        else {}
    )
    claimed = {pgc for pgc in record_pgc_by_id.values() if pgc is not None}
    return resolve_batch(
        group_inputs(inputs),
        record_pgc_by_id,
        layer2_pgcs(list(claimed)),
        # Deduplicated here rather than in SQL: an ordered DISTINCT aggregate forces a sort over all name matches.
        {row["design"]: sorted(set(row["same_name_pgcs"] or [])) for row in inputs if row["design"] is not None},
        resolver,
    )
