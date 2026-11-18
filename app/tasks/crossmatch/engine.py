import math
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import structlog

from app.lib.storage import enums
from app.specs import adminapi as spec
from app.tasks import repository
from app.tasks.crossmatch.models import (
    CrossmatchResult,
    CrossmatchStatus,
    Neighbor,
    PendingReason,
    RecordEvidence,
    TriageStatus,
)
from app.tasks.crossmatch.resolver import Resolver

C_M_S = 299792458

ProgressCallback = Callable[[float, str], None]
DistributionCallback = Callable[[list[dict[str, Any]], str], None]


def distribution_rows(
    counts: Mapping[tuple[CrossmatchStatus, TriageStatus, PendingReason | None], int],
    total: int,
) -> list[dict[str, Any]]:
    def pct(n: int) -> float:
        return round((100.0 * n / total) if total else 0.0, 1)

    ordered = sorted(
        counts,
        key=lambda key: (-counts[key], key[0].value, key[1].value, key[2].value if key[2] is not None else ""),
    )
    return [
        {
            "status": status.value,
            "triage": triage.value,
            "reason": reason.value if reason is not None else "",
            "count": counts[(status, triage, reason)],
            "percent": pct(counts[(status, triage, reason)]),
        }
        for status, triage, reason in ordered
        if counts[(status, triage, reason)] > 0
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


def _group_batch(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, dict[str, Any]], str]:
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


def _resolve_batch(
    by_record: Mapping[str, Mapping[str, Any]],
    record_pgc_by_id: Mapping[str, int | None],
    existing_pgcs: set[int],
    design_to_pgcs: Mapping[str, list[int]],
    resolver: Resolver,
    print_pending: bool,
    log: structlog.stdlib.BoundLogger,
) -> list[tuple[str, CrossmatchResult]]:
    results: list[tuple[str, CrossmatchResult]] = []
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
        results.append((record_id, result))
        if print_pending and result.triage_status == TriageStatus.PENDING:
            reason = result.pending_reason.value if result.pending_reason is not None else "unknown"
            log.warning("pending crossmatch", record_id=record_id, reason=reason)
    return results


def run(
    repo: repository.Repository,
    params: spec.CrossmatchParams,
    log: structlog.stdlib.BoundLogger,
    on_progress: ProgressCallback,
    on_distribution: DistributionCallback,
) -> None:
    resolver = Resolver(
        radius_deg=params.radius / 3600.0,
        pgc_column=params.pgc_column.strip() or None,
        redshift_tolerance=params.redshift_tolerance if params.redshift_tolerance > 0 else None,
    )
    table_id, total_records = repo.crossmatch_table(params.table_name)
    on_progress(0, f"Starting crossmatch for {params.table_name} ({total_records} records)")

    counts: dict[tuple[CrossmatchStatus, TriageStatus, PendingReason | None], int] = defaultdict(int)
    total = 0
    last_id = ""
    try:
        while True:
            rows = repo.fetch_crossmatch_neighbors(table_id, last_id, params.batch_size, resolver.search_radius_deg)
            by_record, last_id = _group_batch(rows)
            if not by_record:
                break

            record_ids = list(by_record)
            record_pgc_by_id = (
                repo.fetch_claimed_pgcs(params.table_name, resolver.pgc_column, record_ids)
                if resolver.pgc_column is not None
                else {}
            )
            claimed = {pgc for pgc in record_pgc_by_id.values() if pgc is not None}
            existing_pgcs = repo.layer2_pgcs(list(claimed))
            designations = [rec["new_design"] for rec in by_record.values() if rec["new_design"] is not None]
            design_to_pgcs = repo.pgcs_by_designation(designations)
            batch_results = _resolve_batch(
                by_record,
                record_pgc_by_id,
                existing_pgcs,
                design_to_pgcs,
                resolver,
                params.print_pending,
                log,
            )
            for _record_id, result in batch_results:
                counts[(result.status, result.triage_status, result.pending_reason)] += 1
                total += 1
            if params.write and batch_results:
                repo.set_crossmatch_results(results_to_rows(batch_results))
            progress = 100.0 if total_records == 0 else min(100.0, 100.0 * total / total_records)
            on_progress(min(progress, 99.0), f"Processed {total} / {total_records} records")
            table = distribution_rows(counts, total)
            if table:
                on_distribution(table, f"{total} records crossmatched")
    finally:
        on_progress(100, "Finished")
        table = distribution_rows(counts, total)
        if table:
            on_distribution(table, f"Final: {total} records")
