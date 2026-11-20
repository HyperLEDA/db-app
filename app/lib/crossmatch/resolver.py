from app.lib.crossmatch.models import CrossmatchResult, CrossmatchStatus, Neighbor, RecordEvidence, TriageStatus
from app.lib.crossmatch.parameters import (
    decide_matched,
    empty_matches,
    enabled_parameters,
    evaluate_candidate,
    prefer_candidates,
)


class Resolver:
    def __init__(
        self,
        radius_deg: float,
        pgc_column: str | None = None,
        redshift_tolerance: float | None = None,
        *,
        include_pgc: bool = False,
        include_redshift: bool = False,
        include_nature: bool = False,
    ) -> None:
        self._radius_deg = radius_deg
        self._pgc_column = pgc_column if include_pgc else None
        self._redshift_tolerance = redshift_tolerance if include_redshift else None
        self._parameter_names = enabled_parameters(
            pgc_enabled=self._pgc_column is not None,
            redshift_enabled=self._redshift_tolerance is not None,
            nature_enabled=include_nature,
        )

    @property
    def search_radius_deg(self) -> float:
        return self._radius_deg

    @property
    def pgc_column(self) -> str | None:
        return self._pgc_column

    def resolve(self, evidence: RecordEvidence) -> CrossmatchResult:
        candidates = self._candidates(evidence)
        unknown_pgc = (
            self._pgc_column is not None
            and evidence.record_pgc is not None
            and not evidence.claimed_pgc_exists_in_layer2
        )
        empty = empty_matches(self._parameter_names)
        if not candidates:
            return CrossmatchResult(
                status=CrossmatchStatus.NEW,
                triage_status=TriageStatus.PENDING if unknown_pgc else TriageStatus.RESOLVED,
                parameters=empty,
            )

        evaluated = [
            (
                candidate,
                evaluate_candidate(
                    evidence, candidate, self._parameter_names, redshift_tolerance=self._redshift_tolerance
                ),
            )
            for candidate in candidates
        ]
        accepted = prefer_candidates(
            [(candidate, matches) for candidate, matches in evaluated if decide_matched(matches)]
        )
        if len(accepted) == 1:
            candidate, matches = accepted[0]
            return CrossmatchResult(
                status=CrossmatchStatus.EXISTING,
                triage_status=TriageStatus.RESOLVED,
                matched_pgc=candidate.pgc,
                parameters=dict(matches),
            )
        pool = accepted if len(accepted) > 1 else evaluated
        if len(pool) == 1:
            candidate, matches = pool[0]
            return CrossmatchResult(
                status=CrossmatchStatus.EXISTING,
                triage_status=TriageStatus.PENDING,
                matched_pgc=candidate.pgc,
                parameters=dict(matches),
            )
        return CrossmatchResult(
            status=CrossmatchStatus.COLLIDING,
            triage_status=TriageStatus.PENDING,
            colliding_pgcs=sorted({candidate.pgc for candidate, _ in pool}),
            parameters=empty,
        )

    def _candidates(self, evidence: RecordEvidence) -> list[Neighbor]:
        by_pgc = {neighbor.pgc: neighbor for neighbor in evidence.neighbors}
        for pgc in evidence.same_name_pgcs or []:
            by_pgc.setdefault(pgc, Neighbor(pgc=pgc, ra=0.0, dec=0.0, distance_deg=float("inf")))
        if self._pgc_column is not None and evidence.record_pgc is not None and evidence.claimed_pgc_exists_in_layer2:
            pgc = evidence.record_pgc
            by_pgc.setdefault(pgc, Neighbor(pgc=pgc, ra=0.0, dec=0.0, distance_deg=float("inf")))
        return list(by_pgc.values())
