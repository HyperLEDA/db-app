from typing import final

import structlog

from app.lib.storage import postgres


@final
class PrivateRepository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)

    def record_action(
        self,
        user_id: int,
        method: str,
        action_description: str | None,
        run_id: str | None,
    ) -> None:
        with self.with_tx():
            if run_id is not None and action_description is not None:
                self._storage.exec(
                    """
                    INSERT INTO private.runs (id, user_id, action_description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    params=[run_id, user_id, action_description],
                )
            self._storage.exec(
                """
                INSERT INTO private.action_log (user_id, run_id, method)
                VALUES (%s, %s, %s)
                """,
                params=[user_id, run_id, method],
            )
