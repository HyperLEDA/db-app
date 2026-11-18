from typing import Any
from uuid import UUID

from prefect import artifacts


class ProgressTracker:
    def __init__(self, key: str) -> None:
        self._artifact_id: UUID | None = None
        self._key = key

    def update(self, progress: float, description: str) -> None:
        if self._artifact_id is None:
            self._artifact_id = artifacts.create_progress_artifact(
                progress=progress,
                description=description,
                key=self._key,
            )
            return
        artifacts.update_progress_artifact(
            artifact_id=self._artifact_id,
            progress=progress,
            description=description,
        )


def emit_table(key: str, rows: list[dict[str, Any]], description: str) -> None:
    artifacts.create_table_artifact(key=key, table=rows, description=description)
