import concurrent.futures
import contextvars
import threading
from collections.abc import Callable
from datetime import timedelta
from time import monotonic

import pydantic
import structlog
from opentelemetry import trace

_tracer = trace.get_tracer("cache.background")


class BackgroundCache[T: pydantic.BaseModel]:
    def __init__(
        self,
        name: str,
        refresh_func: Callable[[], T],
        refresh_frequency: timedelta,
        refresh_timeout: timedelta,
    ) -> None:
        self.name = name
        self._refresh_func = refresh_func
        self.refresh_frequency = refresh_frequency
        self._refresh_timeout = refresh_timeout
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        with _tracer.start_as_current_span("cache.refresh") as span:
            span.set_attribute("cache.name", self.name)
            self._value = self._do_refresh()

    def _do_refresh(self) -> T:
        ctx = contextvars.copy_context()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_in_context, ctx, self._refresh_func)
            try:
                return future.result(timeout=self._refresh_timeout.total_seconds())
            except concurrent.futures.TimeoutError as e:
                raise TimeoutError(f"refresh_func timed out after {self._refresh_timeout}") from e

    def get(self) -> T:
        with self._lock:
            return self._value

    def run(self) -> None:
        log = structlog.get_logger().bind(cache_name=self.name)

        while not self._stop_event.is_set():
            with _tracer.start_as_current_span("cache.refresh") as span:
                span.set_attribute("cache.name", self.name)
                start = monotonic()

                try:
                    new_value = self._do_refresh()
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    log.error("cache refresh failed", reason=str(e), exc_info=True)
                    self._stop_event.wait(timeout=self.refresh_frequency.total_seconds())
                    continue

                elapsed = monotonic() - start
                with self._lock:
                    old_value = self._value
                    self._value = new_value

                old_json = old_value.model_dump_json()
                new_json = new_value.model_dump_json()
                changed = old_json != new_json
                span.set_attribute("cache.duration_seconds", round(elapsed, 3))
                span.set_attribute("cache.size_bytes", len(new_json))
                span.set_attribute("cache.changed", changed)
                log.debug(
                    "cache refreshed",
                    duration_seconds=round(elapsed, 3),
                    size_bytes=len(new_json),
                    changed=changed,
                )
            self._stop_event.wait(timeout=self.refresh_frequency.total_seconds())

    def stop(self) -> None:
        self._stop_event.set()


def _run_in_context[T](ctx: contextvars.Context, fn: Callable[[], T]) -> T:
    return ctx.run(fn)
