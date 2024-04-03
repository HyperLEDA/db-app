from dataclasses import dataclass
import time


@dataclass
class EchoTaskParams:
    sleep_time_seconds: int


def echo_task(params: EchoTaskParams):
    print("echo before sleep")
    time.sleep(params.sleep_time_seconds)
    print("echo after sleep")
