import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor


class TaskResult[T]:
    def __init__(self, future: Future[T | None]) -> None:
        self._future = future

    def result(self) -> T:
        res = self._future.result()
        if res is None:
            raise RuntimeError("Tried to call result() on a failed task")

        return res


class ErrorGroup:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor()
        self._futures: list[Future] = []
        self._error: Exception | None = None
        self._error_lock = threading.Lock()

    def run[T, **P](self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> TaskResult[T]:
        future = self._executor.submit(self._run_with_error_handling, fn, *args, **kwargs)
        self._futures.append(future)

        return TaskResult[T](future)

    def _run_with_error_handling[T, **P](self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T | None:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            with self._error_lock:
                if self._error is None:
                    self._error = e
            return None

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
