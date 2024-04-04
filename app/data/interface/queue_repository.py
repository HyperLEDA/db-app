import abc
from typing import Any, Callable


class QueueRepository(abc.ABC):
    @abc.abstractmethod
    def enqueue(self, func: Callable[..., None], *args: Any) -> None:
        raise NotImplementedError("not implemented")
