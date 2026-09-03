import pytest

from app.lib import containers


def silly_func(limit: int, offset: int) -> list[int]:
    return [offset] * limit


def test_one_batch() -> None:
    it = containers.read_batches(
        silly_func,
        lambda _: True,
        0,
        lambda _, offset: offset + 3,
        batch_size=3,
    )
    with pytest.raises(StopIteration):
        next(it)


def test_two_batches() -> None:
    it = containers.read_batches(
        silly_func,
        lambda _: False,
        0,
        lambda _, offset: offset + 3,
        batch_size=3,
    )
    offset, actual = next(it)
    expected = [0, 0, 0]

    assert actual == expected
    assert offset == 0

    offset, actual = next(it)
    expected = [3, 3, 3]

    assert actual == expected
    assert offset == 3
