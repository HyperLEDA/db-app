import structlog

from app.data import Storage
from app.data.repository import DataRepository
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

    storage = Storage(cfg.storage)
    storage.connect()

    repo = DataRepository(storage)
    actions = usecases.Actions(repo)

    server.start(cfg.server, actions)
    storage.disconnect()
