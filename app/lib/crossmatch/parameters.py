from collections.abc import Mapping, Sequence

from app.lib.crossmatch.models import Neighbor, Parameter, ParameterMatches, RecordEvidence

PARAMETER_ORDER = (
    Parameter.COORDINATES,
    Parameter.NAME,
    Parameter.PGC,
    Parameter.REDSHIFT,
    Parameter.NATURE,
)
_PREFERENCE = (Parameter.PGC, Parameter.NAME)
_SIMILAR = {"G": {"ext", "?", "QSO"}, "ext": {"G", "?", "QSO"}}


def enabled_parameters(*, pgc_enabled: bool, redshift_enabled: bool, nature_enabled: bool) -> tuple[Parameter, ...]:
    enabled = {Parameter.COORDINATES, Parameter.NAME}
    if pgc_enabled:
        enabled.add(Parameter.PGC)
    if redshift_enabled:
        enabled.add(Parameter.REDSHIFT)
    if nature_enabled:
        enabled.add(Parameter.NATURE)
    return tuple(name for name in PARAMETER_ORDER if name in enabled)


def empty_matches(parameter_names: Sequence[Parameter]) -> ParameterMatches:
    return dict.fromkeys(parameter_names, False)


def parameters_payload(matches: Mapping[Parameter, bool]) -> dict[str, bool | None]:
    return {parameter.value: matches.get(parameter) for parameter in PARAMETER_ORDER}


def decide_matched(matches: Mapping[Parameter, bool]) -> bool:
    return matches.get(Parameter.COORDINATES, False) and any(
        matched for name, matched in matches.items() if name != Parameter.COORDINATES
    )


def prefer_candidates(
    accepted: Sequence[tuple[Neighbor, Mapping[Parameter, bool]]],
) -> list[tuple[Neighbor, Mapping[Parameter, bool]]]:
    if len(accepted) <= 1:
        return list(accepted)
    for parameter in _PREFERENCE:
        if parameter not in accepted[0][1]:
            continue
        narrowed = [(c, m) for c, m in accepted if m[parameter]]
        if len(narrowed) == 1:
            return narrowed
    return list(accepted)


def evaluate_candidate(
    evidence: RecordEvidence,
    candidate: Neighbor,
    parameter_names: Sequence[Parameter],
    *,
    redshift_tolerance: float | None,
) -> ParameterMatches:
    same_name = set(evidence.same_name_pgcs or [])
    record_type, other_type = evidence.record_type_name, candidate.type_name
    values = {
        Parameter.COORDINATES: any(n.pgc == candidate.pgc for n in evidence.neighbors),
        Parameter.NAME: evidence.record_designation is not None and candidate.pgc in same_name,
        Parameter.PGC: (
            evidence.record_pgc is not None
            and evidence.claimed_pgc_exists_in_layer2
            and evidence.record_pgc == candidate.pgc
        ),
        Parameter.REDSHIFT: (
            redshift_tolerance is not None
            and evidence.record_redshift is not None
            and candidate.redshift is not None
            and abs(candidate.redshift - evidence.record_redshift) < redshift_tolerance
        ),
        Parameter.NATURE: (
            record_type is not None
            and other_type is not None
            and (record_type == other_type or other_type in _SIMILAR.get(record_type, set()))
        ),
    }
    return {name: values[name] for name in parameter_names}
