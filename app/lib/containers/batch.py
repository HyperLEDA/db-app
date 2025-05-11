from collections.abc import Callable, Iterator
from typing import Any


def read_batches[OutputType: Any, OffsetType: Any](
    func: Callable[(...), OutputType],
    stop_condition: Callable[[OutputType], bool],
    initial_offset: OffsetType,
    offset_changer: Callable[[OutputType, OffsetType], OffsetType],
    *args,
    batch_size: int = 500,
    **kwargs,
) -> Iterator[tuple[OffsetType, OutputType]]:
    """
    Iteratively calls `func` and yields the current offset and the return value of `func`.
    `*args` and `**kwargs` are used as additional arguments to the function.

    `func` *must* have two at least two arguments: `limit` (an integer) and `offset` (any value).
    They will be changed during the iteration.
    `offset_changer` is a function that, based on the last element read and the previous value of the offset,
    changes the offset to a new value. The simplest example of such a function would be:

    ```python
    lambda _, offset: offset + 100
    lambda objects, offset: offset + len(objects)
    lambda objects, _: objects[-1].id
    ```

    Stops iterating when `stop_condition` is `True`.
    The result that satisfies the condition is *not* yielded.
    """

    offset = initial_offset

    while True:
        kwargs["limit"] = batch_size
        kwargs["offset"] = offset
        result = func(*args, **kwargs)

        if stop_condition(result):
            break

        yield offset, result

        offset = offset_changer(result, offset)
