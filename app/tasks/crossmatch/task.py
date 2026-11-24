from collections.abc import Mapping
from typing import Any

import structlog

from app.specs import adminapi as spec
from app.tasks import artifacts, layer2_common
from app.tasks.crossmatch import engine


class CrossmatchTask(layer2_common.Layer2StorageTask):
    def __init__(self, logger: structlog.stdlib.BoundLogger, params: Mapping[str, Any]) -> None:
        super().__init__(logger)
        self._params = dict(params)

    @classmethod
    def name(cls) -> str:
        return "crossmatch"

    def run(self) -> None:
        params = spec.CrossmatchParams.model_validate(self._params)
        progress = artifacts.ProgressTracker("crossmatch-progress")

        def on_progress(value: float, description: str) -> None:
            progress.update(value, description)

        def on_distribution(rows: list[dict[str, Any]], description: str) -> None:
            artifacts.emit_table("crossmatch-distribution", rows, description)

        engine.run(self.repository, params, on_progress, on_distribution, self.log)
