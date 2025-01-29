from collections.abc import Callable


def group_by[T, V](objects: list[T], key_func: Callable[[T], V]) -> dict[V, list[T]]:
    result = {}

    for obj in objects:
        key = key_func(obj)

        if key not in result:
            result[key] = []

        result[key].append(obj)

    return result
