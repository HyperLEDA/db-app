from collections.abc import Callable
from typing import Any

from app.domain.unification.crossmatch.ci_types import CIMatcher


def create_matcher(config: dict[str, Any], available_matchers: dict[str, Callable[..., CIMatcher]]) -> CIMatcher:
    if "type" not in config:
        raise ValueError("Configuration must contain 'type' field")

    matcher_type = config["type"]

    if matcher_type not in available_matchers:
        raise ValueError(f"Unknown matcher type: {matcher_type}")

    matcher_factory = available_matchers[matcher_type]

    params = {k: v for k, v in config.items() if k != "type"}

    processed_params = {}
    for key, value in params.items():
        if isinstance(value, dict) and "type" in value:
            processed_params[key] = create_matcher(value, available_matchers)
        else:
            processed_params[key] = value

    return matcher_factory(**processed_params)
