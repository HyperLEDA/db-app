from typing import final

from app.data import repositories
from app.domain.designation.engine import Rule, RuleEngine
from app.domain.designation.formatter import RuleModel
from app.lib.web.errors import RuleValidationError
from app.presentation import adminapi


def _validate_rule(rule: RuleModel, examples: list[tuple[str, str]] | None = None) -> None:
    engine_rule = Rule(
        id=rule.id,
        priority=rule.priority,
        pattern=rule.pattern,
        template=rule.template,
        transforms=rule.to_engine_rule().transforms,
        examples=examples or [],
    )
    try:
        RuleEngine.compile([engine_rule]).validate_rule(engine_rule)
    except ValueError as e:
        raise RuleValidationError(str(e)) from e


@final
class DesignationRulesManager:
    def __init__(self, rules_repo: repositories.DesignationRulesRepository) -> None:
        self._repo = rules_repo

    def list_rules(self) -> adminapi.ListRulesResponse:
        rules = self._repo.list_rules()
        return adminapi.ListRulesResponse(rules=[adminapi.RuleModel(**r.model_dump()) for r in rules])

    def save_rule(self, request: adminapi.SaveRuleRequest) -> adminapi.SaveRuleResponse:
        rule = RuleModel(**request.rule.model_dump())
        if not rule.id.strip():
            raise RuleValidationError("rule.id is required")
        if rule.enabled:
            examples = [(e.input, e.expected) for e in request.examples]
            _validate_rule(rule, examples)
        saved = self._repo.save_rule(
            rule_id=rule.id,
            priority=rule.priority,
            pattern=rule.pattern,
            template=rule.template,
            transforms=rule.transforms,
            enabled=rule.enabled,
        )
        return adminapi.SaveRuleResponse(rule=adminapi.RuleModel(**saved.model_dump()))
