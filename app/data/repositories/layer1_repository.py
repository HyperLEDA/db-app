from typing import final

import structlog

from app.lib.storage import postgres


@final
class Layer1Repository(postgres.TransactionalPGRepository):
    def __init__(self, storage: postgres.PgStorage, logger: structlog.stdlib.BoundLogger) -> None:
        self._logger = logger
        super().__init__(storage)
