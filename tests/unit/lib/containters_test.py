import unittest

from app.lib import containers


def silly_func(limit: int, offset: int) -> list[int]:
    return [offset] * limit


class TestReadBatches(unittest.TestCase):
    def test_one_batch(self):
        it = containers.read_batches(silly_func, lambda _: True, batch_size=3)
        with self.assertRaises(StopIteration):
            next(it)

    def test_two_batches(self):
        it = containers.read_batches(silly_func, lambda _: False, batch_size=3)
        offset, actual = next(it)
        expected = [0, 0, 0]

        self.assertEqual(actual, expected)
        self.assertEqual(offset, 0)

        offset, actual = next(it)
        expected = [3, 3, 3]

        self.assertEqual(actual, expected)
        self.assertEqual(offset, 3)
