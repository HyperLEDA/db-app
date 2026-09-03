from typing import Any

from app.lib import mock


def returns(func: Any, return_value: Any):
    if not isinstance(func, mock.Mock):
        raise ValueError(f"callable is not a mock: {func}")

    if func.side_effect is None:
        func.side_effect = []

    total_side_effect = []
    total_side_effect.extend(func.side_effect)
    total_side_effect.append(return_value)
    func.side_effect = total_side_effect


def raises(func: Any, exception: type[Exception] | Exception):
    if not isinstance(func, mock.Mock):
        raise ValueError(f"callable is not a mock: {func}")

    func.side_effect = exception
