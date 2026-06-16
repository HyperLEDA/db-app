from collections.abc import Callable
from typing import final

import pydantic

from app.domain.designation.engine import FormatMatch, Rule, RuleEngine, TransformSpec


class RuleModel(pydantic.BaseModel):
    id: str
    priority: int
    pattern: str
    template: str
    transforms: dict[str, list[dict[str, str | None]]] = pydantic.Field(default_factory=dict)
    enabled: bool = True

    def to_engine_rule(self) -> Rule:
        transforms: dict[int, list[TransformSpec]] = {}
        for key, ops in self.transforms.items():
            transforms[int(key)] = [TransformSpec.from_dict(op) for op in ops]
        return Rule(
            id=self.id,
            priority=self.priority,
            pattern=self.pattern,
            template=self.template,
            transforms=transforms,
        )


class RuleSetSnapshot(pydantic.BaseModel):
    version: int
    rules: list[RuleModel]


@final
class DesignationFormatter:
    def __init__(self, get_snapshot: Callable[[], RuleSetSnapshot]) -> None:
        self._get_snapshot = get_snapshot
        self._cached_version: int | None = None
        self._engine: RuleEngine | None = None

    def _ensure_engine(self) -> RuleEngine:
        snapshot = self._get_snapshot()
        if self._engine is None or self._cached_version != snapshot.version:
            rules = [r.to_engine_rule() for r in snapshot.rules if r.enabled]
            self._engine = RuleEngine.compile(rules)
            self._cached_version = snapshot.version
        return self._engine

    def format(self, name: str) -> FormatMatch | None:
        return self._ensure_engine().format(name)

    def format_batch(self, names: list[str]) -> list[tuple[str, FormatMatch | None]]:
        engine = self._ensure_engine()
        results: list[tuple[str, FormatMatch | None]] = []
        for name in names:
            raw = name.strip() if name else ""
            if not raw:
                results.append((name, None))
                continue
            match = engine.format(name)
            results.append((name, match))
        return results
