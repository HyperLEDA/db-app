import socket
import subprocess
import time
from contextlib import closing
from urllib import parse

import requests


def find_free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def wait_for_server(
    url: str,
    *,
    process: subprocess.Popen[bytes] | None = None,
    timeout: float = 30.0,
    poll_interval: float = 0.1,
    request_timeout: float = 1.0,
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            response = requests.get(url, timeout=request_timeout)
            if response.status_code == 200:
                return
        except (requests.RequestException, OSError):
            pass

        if process is not None:
            returncode = process.poll()
            if returncode is not None:
                raise RuntimeError(f"process exited before becoming ready (code={returncode})")

        if time.monotonic() >= deadline:
            if process is not None:
                process.kill()
                process.wait()
            raise RuntimeError(f"server did not become ready within {timeout}s: {url}")

        time.sleep(poll_interval)


class TestSession(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        if url.startswith("/"):
            joined_url = self.base_url.rstrip("/") + url
        else:
            joined_url = parse.urljoin(self.base_url, url)
        return super().request(method, joined_url, *args, **kwargs)
