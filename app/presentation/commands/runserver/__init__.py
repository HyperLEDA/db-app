import structlog

from app.data import Storage, repositories
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

    logger = structlog.get_logger()

    storage = Storage(cfg.storage)
    storage.connect()

    common_repo = repositories.CommonRepository(storage, logger)
    layer0_repo = repositories.Layer0Repository(storage, logger)
    layer1_repo = repositories.Layer1Repository(storage, logger)

    actions = usecases.Actions(common_repo, layer0_repo, layer1_repo, logger)

    server.start(cfg.server, actions)
    storage.disconnect()
