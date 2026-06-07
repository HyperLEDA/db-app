import json
from typing import Any, final

import structlog

from app.domain.designation.formatter import RuleModel, RuleSetSnapshot
from app.lib.storage import postgres


def _row_to_model(row: dict[str, Any]) -> RuleModel:
    transforms = row["transforms"]
    if isinstance(transforms, str):
        transforms = json.loads(transforms)
    return RuleModel(
        id=row["id"],
        priority=int(row["priority"]),
        pattern=row["pattern"],
        template=row["template"],
        transforms=transforms or {},
        enabled=bool(row["enabled"]),
    )


def _transforms_to_json(transforms: dict[str, list[dict[str, str | None]]]) -> str:
    return json.dumps(transforms)


@final
class DesignationRulesRepository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def snapshot(self) -> RuleSetSnapshot:
        rows = self._storage.query(
            """SELECT id, priority, pattern, template, transforms, enabled,
                      EXTRACT(EPOCH FROM MAX(modification_time) OVER ()) AS version_epoch
               FROM designation.format_rules
               WHERE enabled = true
               ORDER BY priority ASC""",
        )
        version = int(rows[0]["version_epoch"]) if rows else 0
        rules = [_row_to_model(r) for r in rows]
        return RuleSetSnapshot(version=version, rules=rules)

    def list_rules(self) -> list[RuleModel]:
        rows = self._storage.query(
            """SELECT id, priority, pattern, template, transforms, enabled
               FROM designation.format_rules
               ORDER BY priority ASC""",
        )
        return [_row_to_model(r) for r in rows]

    def get_rule(self, rule_id: str) -> RuleModel | None:
        rows = self._storage.query(
            """SELECT id, priority, pattern, template, transforms, enabled
               FROM designation.format_rules WHERE id = %s""",
            params=[rule_id],
        )
        if not rows:
            return None
        return _row_to_model(rows[0])

    def save_rule(
        self,
        rule_id: str,
        priority: int,
        pattern: str,
        template: str,
        transforms: dict[str, list[dict[str, str | None]]],
        enabled: bool = True,
    ) -> RuleModel:
        rows = self._storage.query(
            """INSERT INTO designation.format_rules (id, priority, pattern, template, transforms, enabled)
               VALUES (%s, %s, %s, %s, %s::jsonb, %s)
               ON CONFLICT (id) DO UPDATE SET
                 priority = EXCLUDED.priority,
                 pattern = EXCLUDED.pattern,
                 template = EXCLUDED.template,
                 transforms = EXCLUDED.transforms,
                 enabled = EXCLUDED.enabled,
                 modification_time = NOW()
               RETURNING id, priority, pattern, template, transforms, enabled""",
            params=[rule_id, priority, pattern, template, _transforms_to_json(transforms), enabled],
        )
        return _row_to_model(rows[0])
