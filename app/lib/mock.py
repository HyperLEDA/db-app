from __future__ import annotations

import contextlib
import importlib
from collections.abc import Callable, Generator, Mapping, MutableMapping
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])

_sentinel = object()


@dataclass
class _Call:
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    def __getitem__(self, index: int) -> Any:
        if index == 0:
            return self.args
        if index == 1:
            return self.kwargs
        raise IndexError(index)


class Mock:
    def __init__(self, spec: Any | None = None, **kwargs: Any) -> None:
        self._spec = spec
        self._return_value: Any = _sentinel
        self._side_effect: Any = None
        self._calls: list[_Call] = []
        self._children: dict[str, Mock] = {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def return_value(self) -> Any:
        if self._return_value is _sentinel:
            child = self._child("_return_value")
            return child.return_value
        return self._return_value

    @return_value.setter
    def return_value(self, value: Any) -> None:
        self._return_value = value

    @property
    def side_effect(self) -> Any:
        return self._side_effect

    @side_effect.setter
    def side_effect(self, value: Any) -> None:
        self._side_effect = value

    @property
    def call_args(self) -> _Call | None:
        if not self._calls:
            return None
        return self._calls[-1]

    @property
    def call_args_list(self) -> list[_Call]:
        return list(self._calls)

    def _child(self, name: str) -> Mock:
        if name not in self._children:
            self._children[name] = MagicMock()
        return self._children[name]

    def __getattr__(self, name: str) -> Mock:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._child(name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self._calls.append(_Call(args, kwargs))
        if self._side_effect is not None:
            if isinstance(self._side_effect, BaseException):
                raise self._side_effect
            if isinstance(self._side_effect, list):
                effect = self._side_effect.pop(0)
                if isinstance(effect, BaseException):
                    raise effect
                return effect
            if callable(self._side_effect):
                return self._side_effect(*args, **kwargs)
            return self._side_effect
        if self._return_value is not _sentinel:
            return self._return_value
        return MagicMock()

    def assert_called(self) -> None:
        if not self._calls:
            raise AssertionError("Expected mock to have been called")

    def assert_called_once(self) -> None:
        if len(self._calls) != 1:
            raise AssertionError(f"Expected one call, found {len(self._calls)}")

    def assert_called_once_with(self, *args: Any, **kwargs: Any) -> None:
        self.assert_called_once()
        call = self._calls[0]
        if call.args != args or call.kwargs != kwargs:
            raise AssertionError(f"Expected call {args, kwargs}, got {call.args, call.kwargs}")

    def assert_not_called(self) -> None:
        if self._calls:
            raise AssertionError(f"Expected mock not to be called, called {len(self._calls)} times")

    def reset_mock(self) -> None:
        self._calls.clear()
        self._return_value = _sentinel
        self._side_effect = None
        self._children.clear()


class MagicMock(Mock):
    pass


def create_autospec(spec: Any, **kwargs: Any) -> Mock:
    return Mock(spec=spec, **kwargs)


def _resolve_target(target: str) -> tuple[Any, str]:
    parts = target.rsplit(".", 1)
    if len(parts) == 1:
        raise ValueError(f"invalid patch target: {target}")
    module_name, attribute = parts
    module = importlib.import_module(module_name)
    return module, attribute


class _Patch:
    def __init__(
        self,
        target: str,
        new: Any = _sentinel,
        *,
        return_value: Any = _sentinel,
        side_effect: Any = None,
    ) -> None:
        self._target = target
        self._new = new
        self._return_value = return_value
        self._side_effect = side_effect
        self._original: Any = None
        self._module: Any = None
        self._attribute: str = ""

    def _build_replacement(self) -> Any:
        if self._new is not _sentinel:
            return self._new
        replacement = MagicMock()
        if self._return_value is not _sentinel:
            replacement.return_value = self._return_value
        if self._side_effect is not None:
            replacement.side_effect = self._side_effect
        return replacement

    def __enter__(self) -> Any:
        self._module, self._attribute = _resolve_target(self._target)
        self._original = getattr(self._module, self._attribute)
        replacement = self._build_replacement()
        setattr(self._module, self._attribute, replacement)
        return replacement

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> None:
        setattr(self._module, self._attribute, self._original)

    def __call__(self, func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with self as patched:
                return func(*args, patched, **kwargs)

        return cast(F, wrapper)

    def start(self) -> Any:
        return self.__enter__()

    def stop(self) -> None:
        self.__exit__(None, None, None)


@contextlib.contextmanager
def patch_dict(
    mapping: MutableMapping[str, Any],
    values: Mapping[str, Any],
    *,
    clear: bool = False,
) -> Generator[None]:
    original = dict(mapping)
    if clear:
        mapping.clear()
    mapping.update(values)
    try:
        yield
    finally:
        mapping.clear()
        mapping.update(original)


class _PatchDictContext:
    def __init__(
        self,
        mapping: MutableMapping[str, Any],
        values: Mapping[str, Any],
        *,
        clear: bool = False,
    ) -> None:
        self._mapping = mapping
        self._values = values
        self._clear = clear

    def __enter__(self) -> None:
        self._cm = patch_dict(self._mapping, self._values, clear=self._clear)
        self._cm.__enter__()

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: Any) -> None:
        self._cm.__exit__(exc_type, exc, tb)

    def __call__(self, func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with patch_dict(self._mapping, self._values, clear=self._clear):
                return func(*args, **kwargs)

        return cast(F, wrapper)


class _PatchCallable:
    def __call__(
        self,
        target: str,
        new: Any = _sentinel,
        *,
        return_value: Any = _sentinel,
        side_effect: Any = None,
    ) -> _Patch:
        return _Patch(target, new, return_value=return_value, side_effect=side_effect)

    dict = _PatchDictContext


patch = _PatchCallable()

__all__ = ["Mock", "MagicMock", "patch", "create_autospec", "patch_dict"]
