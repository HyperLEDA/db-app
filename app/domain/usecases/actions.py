from typing import final

import structlog

from app import data
from app.domain.usecases import database_actions, queue_actions


@final
class Actions(database_actions.DatabaseActions, queue_actions.QueueActions):
    def __init__(self, db_repo: data.DatabaseRepository, queue_repo: data.QueueRepository) -> None:
        database_actions.DatabaseActions.__init__(self, db_repo, structlog.get_logger())
        queue_actions.QueueActions.__init__(self, queue_repo, structlog.get_logger())
