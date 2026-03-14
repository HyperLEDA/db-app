import threading
import time
import unittest
from datetime import timedelta

import pydantic

from app.lib.cache.cache import BackgroundCache


class DummyModel(pydantic.BaseModel):
    value: int


class BackgroundCacheTest(unittest.TestCase):
    def test_happy_path_no_change(self):
        value = DummyModel(value=1)

        def refresh():
            return value

        cache = BackgroundCache(
            name="test_cache",
            refresh_func=refresh,
            refresh_frequency=timedelta(seconds=0.1),
            refresh_timeout=timedelta(seconds=1),
        )
        self.assertEqual(cache.get().value, 1)
        t = threading.Thread(target=cache.run, daemon=True)
        t.start()
        time.sleep(0.35)
        for _ in range(3):
            self.assertEqual(cache.get().value, 1)
        cache.stop()
        t.join(timeout=1)
        self.assertEqual(cache.get().value, 1)

    def test_happy_path_with_change(self):
        state = {"v": 0}

        def refresh():
            return DummyModel(value=state["v"])

        cache = BackgroundCache(
            name="test_cache",
            refresh_func=refresh,
            refresh_frequency=timedelta(seconds=0.05),
            refresh_timeout=timedelta(seconds=1),
        )
        self.assertEqual(cache.get().value, 0)
        t = threading.Thread(target=cache.run, daemon=True)
        t.start()
        self.assertEqual(cache.get().value, 0)
        state["v"] = 1
        time.sleep(0.15)
        self.assertEqual(cache.get().value, 1)
        state["v"] = 2
        time.sleep(0.15)
        self.assertEqual(cache.get().value, 2)
        cache.stop()
        t.join(timeout=1)

    def test_refresh_fails_then_restores_value_unchanged(self):
        call_count = 0

        def refresh():
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("transient failure")
            return DummyModel(value=42)

        cache = BackgroundCache(
            name="test_cache",
            refresh_func=refresh,
            refresh_frequency=timedelta(seconds=0.05),
            refresh_timeout=timedelta(seconds=1),
        )
        self.assertEqual(cache.get().value, 42)
        t = threading.Thread(target=cache.run, daemon=True)
        t.start()
        time.sleep(0.2)
        self.assertEqual(cache.get().value, 42)
        cache.stop()
        t.join(timeout=1)
        self.assertEqual(cache.get().value, 42)

    def test_refresh_fails_during_init_raises(self):
        def refresh():
            raise ValueError("init failed")

        with self.assertRaises(ValueError) as ctx:
            BackgroundCache(
                name="test_cache",
                refresh_func=refresh,
                refresh_frequency=timedelta(seconds=1),
                refresh_timeout=timedelta(seconds=1),
            )
        self.assertIn("init failed", str(ctx.exception))
