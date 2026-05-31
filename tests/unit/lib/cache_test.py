import threading
import unittest
from datetime import timedelta
from time import monotonic

import pydantic

from app.lib.cache import BackgroundCache


class SampleSnapshot(pydantic.BaseModel):
    value: int


class BackgroundCacheTest(unittest.TestCase):
    def test_get_returns_initial_value(self) -> None:
        cache = BackgroundCache(
            "test",
            lambda: SampleSnapshot(value=1),
            refresh_frequency=timedelta(hours=1),
            refresh_timeout=timedelta(seconds=1),
        )
        self.assertEqual(cache.get().value, 1)
        cache.stop()

    def test_run_refreshes_value(self) -> None:
        counter = {"n": 0}

        def refresh() -> SampleSnapshot:
            counter["n"] += 1
            return SampleSnapshot(value=counter["n"])

        cache = BackgroundCache(
            "test",
            refresh,
            refresh_frequency=timedelta(milliseconds=50),
            refresh_timeout=timedelta(seconds=1),
        )
        thread = threading.Thread(target=cache.run, daemon=True)
        thread.start()

        deadline = monotonic() + 2.0
        while monotonic() < deadline:
            if cache.get().value >= 2:
                break
            threading.Event().wait(0.05)

        cache.stop()
        thread.join(timeout=2.0)
        self.assertGreaterEqual(cache.get().value, 2)

    def test_run_keeps_old_value_on_refresh_failure(self) -> None:
        fail_refresh = {"v": False}

        def refresh() -> SampleSnapshot:
            if fail_refresh["v"]:
                raise RuntimeError("refresh failed")
            return SampleSnapshot(value=1)

        cache = BackgroundCache(
            "test",
            refresh,
            refresh_frequency=timedelta(milliseconds=50),
            refresh_timeout=timedelta(seconds=1),
        )
        self.assertEqual(cache.get().value, 1)

        fail_refresh["v"] = True
        thread = threading.Thread(target=cache.run, daemon=True)
        thread.start()

        threading.Event().wait(0.2)

        cache.stop()
        thread.join(timeout=2.0)
        self.assertEqual(cache.get().value, 1)
