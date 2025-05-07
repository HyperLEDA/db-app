import unittest

from parameterized import param, parameterized

from app.data import model
from app.domain.processing.crossmatch import compute_ci_result


class TestCrossmatchCIResult(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "object is new",
                {"a": set(), "b": set(), "c": set()},
                model.CIResultObjectNew(),
            ),
            param(
                "all empty one nonempty",
                {"a": set(), "b": set(), "c": {1}},
                model.CIResultObjectCollision({"a": set(), "b": set(), "c": {1}}),
            ),
            param(
                "all nonempty no intersection",
                {"a": {12, 34}, "b": {56, 67}},
                model.CIResultObjectCollision({"a": {12, 34}, "b": {56, 67}}),
            ),
            param(
                "all nonempty one intersection",
                {"a": {12, 34}, "b": {34, 56}},
                model.CIResultObjectExisting(34),
            ),
            param(
                "all nonempty several intersections",
                {"a": {12, 34, 56}, "b": {34, 56, 78}},
                model.CIResultObjectCollision({"a": {12, 34, 56}, "b": {34, 56, 78}}),
            ),
        ]
    )
    def test_table(self, name, input_data, expected):
        actual = compute_ci_result(input_data)

        self.assertEqual(actual, expected)
