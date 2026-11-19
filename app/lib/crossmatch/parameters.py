from collections.abc import Callable, Mapping, Sequence

from app.lib.crossmatch.models import Neighbor, Parameter, ParameterMatches, RecordEvidence

PARAMETER_ORDER: tuple[Parameter, ...] = (
    Parameter.COORDINATES,
    Parameter.NAME,
    Parameter.PGC,
    Parameter.REDSHIFT,
    Parameter.TYPE,
)

_AUTO_MATCH_PARAMETERS: frozenset[Parameter] = frozenset({Parameter.COORDINATES, Parameter.REDSHIFT, Parameter.TYPE})
_PREFERENCE_PARAMETERS: tuple[Parameter, ...] = (Parameter.PGC, Parameter.NAME)

_SIMILAR_TYPE_MAP = {
    "G": {"ext", "?", "QSO"},
    "ext": {"G", "?", "QSO"},
}

type ParameterEvaluator = Callable[[RecordEvidence, Neighbor, float | None], bool]


def enabled_parameters(
    *,
    pgc_enabled: bool,
    redshift_enabled: bool,
    nature_enabled: bool,
) -> tuple[Parameter, ...]:
    enabled: set[Parameter] = {Parameter.COORDINATES, Parameter.NAME}
    if pgc_enabled:
        enabled.add(Parameter.PGC)
    if redshift_enabled:
        enabled.add(Parameter.REDSHIFT)
    if nature_enabled:
        enabled.add(Parameter.TYPE)
    return tuple(name for name in PARAMETER_ORDER if name in enabled)


def empty_matches(parameter_names: Sequence[Parameter]) -> ParameterMatches:
    return dict.fromkeys(parameter_names, False)


def parameters_payload(matches: Mapping[Parameter, bool]) -> dict[str, bool | None]:
    return {
        Parameter.COORDINATES.value: matches.get(Parameter.COORDINATES),
        Parameter.NAME.value: matches.get(Parameter.NAME),
        Parameter.PGC.value: matches.get(Parameter.PGC),
        Parameter.REDSHIFT.value: matches.get(Parameter.REDSHIFT),
        Parameter.TYPE.value: matches.get(Parameter.TYPE),
    }


def decide_matched(matches: Mapping[Parameter, bool]) -> bool:
    required = [name for name in _AUTO_MATCH_PARAMETERS if name in matches]
    if not required:
        required = list(matches)
    return bool(required) and all(matches[name] for name in required)


def prefer_candidates(
    accepted: Sequence[tuple[Neighbor, Mapping[Parameter, bool]]],
) -> list[tuple[Neighbor, Mapping[Parameter, bool]]]:
    if len(accepted) <= 1:
        return list(accepted)
    for parameter in _PREFERENCE_PARAMETERS:
        if parameter not in accepted[0][1]:
            continue
        narrowed = [(candidate, matches) for candidate, matches in accepted if matches[parameter]]
        if len(narrowed) == 1:
            return narrowed
    return list(accepted)


def _types_match(record_type: str, other_type: str) -> bool:
    return record_type == other_type or other_type in _SIMILAR_TYPE_MAP.get(record_type, set())


def _match_coordinates(evidence: RecordEvidence, candidate: Neighbor, _redshift_tolerance: float | None) -> bool:
    return any(neighbor.pgc == candidate.pgc for neighbor in evidence.neighbors)


def _match_name(evidence: RecordEvidence, candidate: Neighbor, _redshift_tolerance: float | None) -> bool:
    same_name = set(evidence.same_name_pgcs or [])
    return evidence.record_designation is not None and candidate.pgc in same_name


def _match_pgc(evidence: RecordEvidence, candidate: Neighbor, _redshift_tolerance: float | None) -> bool:
    return (
        evidence.record_pgc is not None
        and evidence.claimed_pgc_exists_in_layer2
        and evidence.record_pgc == candidate.pgc
    )


def _match_redshift(evidence: RecordEvidence, candidate: Neighbor, redshift_tolerance: float | None) -> bool:
    return (
        redshift_tolerance is not None
        and evidence.record_redshift is not None
        and candidate.redshift is not None
        and abs(candidate.redshift - evidence.record_redshift) < redshift_tolerance
    )


def _match_type(evidence: RecordEvidence, candidate: Neighbor, _redshift_tolerance: float | None) -> bool:
    return (
        evidence.record_type_name is not None
        and candidate.type_name is not None
        and _types_match(evidence.record_type_name, candidate.type_name)
    )


_EVALUATORS: dict[Parameter, ParameterEvaluator] = {
    Parameter.COORDINATES: _match_coordinates,
    Parameter.NAME: _match_name,
    Parameter.PGC: _match_pgc,
    Parameter.REDSHIFT: _match_redshift,
    Parameter.TYPE: _match_type,
}


def evaluate_candidate(
    evidence: RecordEvidence,
    candidate: Neighbor,
    parameter_names: Sequence[Parameter],
    *,
    redshift_tolerance: float | None,
) -> ParameterMatches:
    return {name: _EVALUATORS[name](evidence, candidate, redshift_tolerance) for name in parameter_names}
