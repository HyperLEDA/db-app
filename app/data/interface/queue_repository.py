import abc
from typing import Any, Callable


class QueueRepository(abc.ABC):
    @abc.abstractmethod
    def enqueue(self, job: Callable[..., None], *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("not implemented")
