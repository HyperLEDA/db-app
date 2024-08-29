import structlog

from app import commands
from app.commands.runserver import config
from app.data import repositories
from app.lib import auth, clients
from app.lib.storage import postgres, redis
from app.presentation import server


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

    authenticator = auth.PostgresAuthenticator(pg_storage)
    depot = commands.Depot(
        common_repo=repositories.CommonRepository(pg_storage, logger),
        layer0_repo=repositories.Layer0Repository(pg_storage, logger),
        layer2_repo=repositories.Layer2Repository(pg_storage, logger),
        tmp_data_repo=repositories.TmpDataRepositoryImpl(pg_storage),
        queue_repo=repositories.QueueRepository(redis_storage, cfg.storage, logger),
        authenticator=authenticator,
        clients=clients.Clients(cfg.clients.ads_token),
    )

    try:
        server.start(cfg.server, authenticator, depot, logger)
    except Exception as e:
        logger.exception(e)
    finally:
        redis_storage.disconnect()
        pg_storage.disconnect()
