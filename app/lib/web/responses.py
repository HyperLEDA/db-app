from collections.abc import Mapping
from typing import Any


class APIOkResponse:
    def __init__(self, data: Any, status: int = 200) -> None:
        self.data = data
        self.status = status

    def __await__(self):
        return self.data.__await__()


class BinaryResponse:
    def __init__(
        self, data: bytes, content_type: str, status: int = 200, headers: Mapping[str, str] | None = None
    ) -> None:
        self.data = data
        self.content_type = content_type
        self.status = status
        self.headers = headers or {}

    async def __await__(self):
        return self
