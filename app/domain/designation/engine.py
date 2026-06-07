import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Self, final


class TransformOp(StrEnum):
    UPPER = "upper"
    LOWER = "lower"
    CAPITALIZE = "capitalize"
    STRIP_ZEROS = "strip_zeros"
    ZFILL = "zfill"
    ROMAN_OR_INT = "roman_or_int"
    DEFAULT = "default"


_ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def _roman_to_int(s: str) -> int:
    val = 0
    for i in range(len(s)):
        if i + 1 < len(s) and _ROMAN[s[i]] < _ROMAN[s[i + 1]]:
            val -= _ROMAN[s[i]]
        else:
            val += _ROMAN[s[i]]
    return val


@dataclass(frozen=True)
class TransformSpec:
    op: TransformOp
    arg: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(op=TransformOp(data["op"]), arg=data.get("arg"))

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"op": self.op.value}
        if self.arg is not None:
            result["arg"] = self.arg
        return result


def apply_transform(value: str, spec: TransformSpec) -> str:
    match spec.op:
        case TransformOp.UPPER:
            return value.upper()
        case TransformOp.LOWER:
            return value.lower()
        case TransformOp.CAPITALIZE:
            return value.capitalize()
        case TransformOp.STRIP_ZEROS:
            return str(int(value)) if value.isdigit() else value
        case TransformOp.ZFILL:
            width = int(spec.arg or "0")
            return value.zfill(width)
        case TransformOp.ROMAN_OR_INT:
            if value.isdigit():
                return str(int(value))
            return str(_roman_to_int(value.upper()))
        case TransformOp.DEFAULT:
            return spec.arg if not value else value


@dataclass(frozen=True)
class Rule:
    id: str
    priority: int
    pattern: str
    template: str
    transforms: dict[int, list[TransformSpec]] = field(default_factory=dict)
    examples: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class FormatMatch:
    formatted: str
    rule_id: str


@final
class CompiledRule:
    def __init__(self, rule: Rule) -> None:
        self.rule = rule
        self._pattern = re.compile(rule.pattern, re.IGNORECASE)

    def match(self, value: str) -> str | None:
        m = self._pattern.match(value)
        if m is None:
            return None
        groups: list[str] = []
        for i in range(1, m.lastindex + 1 if m.lastindex else 0):
            raw = m.group(i) or ""
            transformed = raw
            for spec in self.rule.transforms.get(i, []):
                if spec.op == TransformOp.DEFAULT and transformed:
                    continue
                transformed = apply_transform(transformed, spec)
            groups.append(transformed)
        return self.rule.template.format(*groups)


@final
class RuleEngine:
    def __init__(self, compiled: list[CompiledRule]) -> None:
        self._compiled = compiled

    @classmethod
    def compile(cls, rules: list[Rule]) -> Self:
        enabled = sorted(rules, key=lambda r: r.priority)
        return cls([CompiledRule(r) for r in enabled])

    def format(self, name: str) -> FormatMatch | None:
        value = name.strip() if name else ""
        if not value:
            return None
        for compiled in self._compiled:
            formatted = compiled.match(value)
            if formatted is not None:
                return FormatMatch(
                    formatted=formatted,
                    rule_id=compiled.rule.id,
                )
        return None

    def validate_rule(self, rule: Rule) -> None:
        re.compile(rule.pattern, re.IGNORECASE)
        for group_idx, specs in rule.transforms.items():
            for spec in specs:
                if spec.op == TransformOp.ZFILL and spec.arg is None:
                    raise ValueError(f"zfill transform on group {group_idx} requires arg")
                if spec.op == TransformOp.DEFAULT and spec.arg is None:
                    raise ValueError(f"default transform on group {group_idx} requires arg")
        engine = RuleEngine.compile([rule])
        for raw, expected in rule.examples:
            result = engine.format(raw)
            if result is None or result.formatted != expected:
                got = result.formatted if result else None
                raise ValueError(f"example {raw!r}: expected {expected!r}, got {got!r}")
