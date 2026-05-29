import hashlib
import json

from app.lib.audit import interface
from app.lib.storage import postgres


def run_id(user_id: int, method: str, action_description: str) -> str:
    return hashlib.sha256(f"{user_id}\x00{method}\x00{action_description}".encode()).hexdigest()


class NoopActionRecorder(interface.ActionRecorder):
    def record_action(
        self,
        user_id: int,
        method: str,
        action_description: str | None,
        request: dict[str, object] | None,
    ) -> None:
        pass


class PostgresActionRecorder(postgres.TransactionalPGRepository, interface.ActionRecorder):
    def __init__(self, storage: postgres.PgStorage) -> None:
        super().__init__(storage)

    def record_action(
        self,
        user_id: int,
        method: str,
        action_description: str | None,
        request: dict[str, object] | None,
    ) -> None:
        resolved_run_id = run_id(user_id, method, action_description) if action_description is not None else None
        with self.with_tx():
            if resolved_run_id is not None and action_description is not None:
                self._storage.exec(
                    """
                    INSERT INTO private.runs (id, user_id, action_description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    params=[resolved_run_id, user_id, action_description],
                )
            self._storage.exec(
                """
                INSERT INTO private.action_log (user_id, run_id, method, request)
                VALUES (%s, %s, %s, %s::jsonb)
                """,
                params=[user_id, resolved_run_id, method, json.dumps(request) if request is not None else None],
            )
