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
    __: structlog.stdlib.BoundLogger,
) -> None:
    print(f"sleeping for {params.sleep_time_seconds} seconds")
    time.sleep(params.sleep_time_seconds)
    print("done!")
