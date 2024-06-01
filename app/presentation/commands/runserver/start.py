import structlog

from app.data import repositories
from app.domain import usecases
from app.lib import auth, clients
from app.lib.storage import postgres, redis
from app.presentation import server
from app.presentation.commands.runserver import config


def start(config_path: str):
    cfg = config.parse_config(config_path)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
    )

    logger: structlog.stdlib.BoundLogger = structlog.get_logger()

    pg_storage = postgres.PgStorage(cfg.storage, logger)
    pg_storage.connect()

    redis_storage = redis.RedisQueue(cfg.queue, logger)
    redis_storage.connect()

    common_repo = repositories.CommonRepository(pg_storage, logger)
    layer0_repo = repositories.Layer0Repository(pg_storage, logger)
    queue_repo = repositories.QueueRepository(redis_storage, cfg.storage, logger)

    authenticator = auth.PostgresAuthenticator(pg_storage)

    client = clients.Clients(cfg.clients.ads_token)

    actions = usecases.Actions(
        common_repo,
        layer0_repo,
        queue_repo,
        authenticator,
        client,
        cfg.storage,
        logger,
    )

    try:
        server.start(cfg.server, authenticator, actions, logger)
    except Exception as e:
        logger.exception(e)
    finally:
        redis_storage.disconnect()
        pg_storage.disconnect()
