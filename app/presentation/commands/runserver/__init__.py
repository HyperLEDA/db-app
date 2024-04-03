import redis
import structlog

from app.data import postgres as data_postgres
from app.data import redis as data_redis
from app.domain import usecases
from app.presentation import server
from app.presentation.commands.runserver.config import parse_config


def start(config_path: str):
    cfg = parse_config(config_path)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    storage = data_postgres.Storage(cfg.storage)
    storage.connect()

    repo = data_postgres.DataRepository(storage)
    queue = data_redis.QueueRepository(cfg.queue)

    actions = usecases.Actions(repo, queue)

    server.start(cfg.server, actions)
    storage.disconnect()
