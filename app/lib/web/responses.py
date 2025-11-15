from typing import Any


class APIOkResponse:
    def __init__(self, data: Any, status: int = 200) -> None:
        self.data = data
        self.status = status

    def __await__(self):
        return self.data.__await__()
