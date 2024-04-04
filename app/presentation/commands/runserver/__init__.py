import redis
import structlog

from app.data import PgStorage, repositories
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

    pg_storage = PgStorage(cfg.storage)
    pg_storage.connect()

    common_repo = repositories.CommonRepository(pg_storage, logger)
    layer0_repo = repositories.Layer0Repository(pg_storage, logger)
    layer1_repo = repositories.Layer1Repository(pg_storage, logger)
    queue_repo = repositories.QueueRepository(cfg.queue, "default", logger)

    actions = usecases.Actions(common_repo, layer0_repo, layer1_repo, queue_repo, logger)

    server.start(cfg.server, actions)
    pg_storage.disconnect()
