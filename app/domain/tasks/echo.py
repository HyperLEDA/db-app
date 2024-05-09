import time
from dataclasses import dataclass

import structlog

from app.lib.storage import postgres


@dataclass
class EchoTaskParams:
    sleep_time_seconds: int


def echo_task(
    _: postgres.PgStorage,
    params: EchoTaskParams,
    logger: structlog.stdlib.BoundLogger,
) -> None:
    logger.info("sleeping", seconds=params.sleep_time_seconds)
    time.sleep(params.sleep_time_seconds)
    logger.info("done!")
