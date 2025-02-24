from pathlib import Path

import yaml

from app import tasks


def parse_config(path: str) -> tasks.Config:
    data = yaml.safe_load(Path(path).read_text())

    return tasks.ConfigSchema().load(data)
