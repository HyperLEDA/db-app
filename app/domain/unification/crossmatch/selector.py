from collections.abc import Mapping
from typing import Any

from app.data.repositories.layer2 import Filter


def create_selector(config: dict[str, Any], available_filters: Mapping[str, type[Filter]]) -> Filter:
    if "type" not in config:
        raise ValueError("Configuration must contain 'type' field")

    filter_type = config["type"]

    if filter_type not in available_filters:
        raise ValueError(f"Unknown filter type: {filter_type}")

    filter_class = available_filters[filter_type]

    params = {k: v for k, v in config.items() if k != "type"}

    processed_params = {}
    for key, value in params.items():
        if isinstance(value, dict) and "type" in value:
            processed_params[key] = create_selector(value, available_filters)
        elif isinstance(value, list) and value and isinstance(value[0], dict) and "type" in value[0]:
            processed_params[key] = [create_selector(item, available_filters) for item in value]
        else:
            processed_params[key] = value

    return filter_class(**processed_params)
