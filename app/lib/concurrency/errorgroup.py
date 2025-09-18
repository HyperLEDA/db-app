import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor


class ErrorGroup:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor()
        self._futures: list[Future] = []
        self._error: Exception | None = None
        self._error_lock = threading.Lock()

    def run[**P](self, fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> None:
        self._futures.append(
            self._executor.submit(self._run_with_error_handling, fn, *args, **kwargs),
        )

    def _run_with_error_handling[**P](self, fn: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> None:
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
