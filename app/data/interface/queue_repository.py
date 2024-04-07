import abc
from typing import Any, Callable


class QueueRepository(abc.ABC):
    @abc.abstractmethod
    def enqueue(self, task_id: int, func: Callable[..., None], *args: Any) -> None:
        raise NotImplementedError("not implemented")
