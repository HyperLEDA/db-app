from collections.abc import Callable, Iterator


def read_batches[T](
    func: Callable[(...), T],
    stop_condition: Callable[[T], bool],
    *args,
    batch_size: int = 500,
    initial_offset: int = 0,
    **kwargs,
) -> Iterator[tuple[int, T]]:
    """
    Iteratively calls `func` and yields current offset and the return value of func.
    `*args` and `**kwargs` are used as other arguments to the function.

    `func` MUST have two at least two integer arguments: `limit` and `offset`.
    They will be changed during the iteration.

    Stops iterating when `stop_condition` is `True`.
    """

    offset = initial_offset

    while True:
        kwargs["limit"] = batch_size
        kwargs["offset"] = offset
        result = func(*args, **kwargs)

        yield offset, result

        offset += batch_size

        if stop_condition(result):
            break
