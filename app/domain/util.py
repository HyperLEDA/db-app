import asyncio


class GlobalDBLock:
    _lock = asyncio.Lock()

    @staticmethod
    def get() -> asyncio.Lock:
        return GlobalDBLock._lock
