from typing import Any
from unittest import mock


def returns(func: Any, return_value: Any):
    """
    Mocks return value of `func`. Can safely be called several times to mock sequential calls.

    If called only once, all consecutive calls will return `StopIteration`.
    """
    if not isinstance(func, mock.Mock):
        raise ValueError(f"callable is not a mock: {func}")

    if func.side_effect is None:
        func.side_effect = []

    total_side_effect = []
    total_side_effect.extend(func.side_effect)
    total_side_effect.append(return_value)
    func.side_effect = total_side_effect


def raises(func: Any, exception: type[Exception] | Exception):
    """
    Mocks raising an Exception from the function. Can only be called once.
    """
    if not isinstance(func, mock.Mock):
        raise ValueError(f"callable is not a mock: {func}")

    func.side_effect = exception
