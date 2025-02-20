import unittest

from astropy import units as u
from parameterized import param, parameterized

from app.data import model
from app.domain import converters, processing
from app.domain.processing.crossmatch import compute_ci_result
from app.domain.processing.mark_objects import get_converters


class TestGetConverters(unittest.TestCase):
    def test_valid_columns(self):
        columns = [
            model.ColumnDescription("name", "text", ucd="meta.id"),
            model.ColumnDescription("ra", "float", ucd="pos.eq.ra", unit=u.rad),
            model.ColumnDescription("dec", "float", ucd="pos.eq.dec", unit=u.rad),
        ]

        expected = {
            converters.ICRSConverter.name(),
            converters.NameConverter.name(),
        }

        actual = get_converters(columns)

        self.assertEqual(expected, {a.name() for a in actual})

    def test_unparsable_columns(self):
        columns = [
            model.ColumnDescription("name", "text"),
            model.ColumnDescription("ra", "float", unit=u.rad),
            model.ColumnDescription("dec", "float", unit=u.rad),
        ]

        with self.assertRaises(RuntimeError):
            get_converters(columns)


class TestCrossmatchCIResult(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "object is new",
                {"a": set(), "b": set(), "c": set()},
                processing.CIResultObjectNew(),
            ),
            param(
                "all empty one nonempty",
                {"a": set(), "b": set(), "c": {1}},
                processing.CIResultObjectCollision({"a": set(), "b": set(), "c": {1}}),
            ),
            param(
                "all nonempty no intersection",
                {"a": {12, 34}, "b": {56, 67}},
                processing.CIResultObjectCollision({"a": {12, 34}, "b": {56, 67}}),
            ),
            param(
                "all nonempty one intersection",
                {"a": {12, 34}, "b": {34, 56}},
                processing.CIResultObjectExisting(34),
            ),
            param(
                "all nonempty several intersections",
                {"a": {12, 34, 56}, "b": {34, 56, 78}},
                processing.CIResultObjectCollision({"a": {12, 34, 56}, "b": {34, 56, 78}}),
            ),
        ]
    )
    def test_table(self, name, input_data, expected):
        actual = compute_ci_result(input_data)

        self.assertEqual(actual, expected)
