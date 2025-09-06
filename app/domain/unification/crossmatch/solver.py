from collections.abc import Callable
from typing import Any

from app.domain.unification.crossmatch.ci_types import CISolver


def create_solver(config: dict[str, Any], available_solvers: dict[str, Callable[..., CISolver]]) -> CISolver:
    if "type" not in config:
        raise ValueError("Configuration must contain 'type' field")

    solver_type = config["type"]

    if solver_type not in available_solvers:
        raise ValueError(f"Unknown solver type: {solver_type}")

    solver_factory = available_solvers[solver_type]

    params = {k: v for k, v in config.items() if k != "type"}

    processed_params = {}
    for key, value in params.items():
        if isinstance(value, dict) and "type" in value:
            processed_params[key] = create_solver(value, available_solvers)
        else:
            processed_params[key] = value

    return solver_factory(**processed_params)
