from typing import final

import structlog

from app import data
from app.domain.usecases import database_actions, queue_actions


@final
class Actions(database_actions.DatabaseActions, queue_actions.QueueActions):
    def __init__(self, repo: data.Repository) -> None:
        database_actions.DatabaseActions.__init__(self, repo, structlog.get_logger())
        queue_actions.QueueActions.__init__(self, structlog.get_logger())
