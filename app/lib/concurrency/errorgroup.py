import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any


class ErrorGroup:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor()
        self._futures: list[Future] = []
        self._error: Exception | None = None
        self._error_lock = threading.Lock()

    def run(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        future = self._executor.submit(self._run_with_error_handling, fn, *args, **kwargs)
        self._futures.append(future)

    def _run_with_error_handling(self, fn: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        try:
            fn(*args, **kwargs)
        except Exception as e:
            with self._error_lock:
                if self._error is None:
                    self._error = e

    def wait(self) -> None:
        try:
            for future in self._futures:
                future.result()
                if self._error is not None:
                    break
        finally:
            self._executor.shutdown(wait=False)

            for future in self._futures:
                if not future.done():
                    future.cancel()

        if self._error is not None:
            raise self._error
