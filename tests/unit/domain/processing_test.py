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
                [set(), set(), set()],
                processing.CIResultObjectNew(),
            ),
            param(
                "all empty one nonempty",
                [set(), set(), {1}],
                processing.CIResultObjectCollision({1}),
            ),
            param(
                "all nonempty no intersection",
                [{12, 34}, {56, 67}],
                processing.CIResultObjectCollision({12, 34, 56, 67}),
            ),
            param(
                "all nonempty one intersection",
                [{12, 34}, {34, 56}],
                processing.CIResultObjectExisting(34),
            ),
            param(
                "all nonempty several intersections",
                [{12, 34, 56}, {34, 56, 78}],
                processing.CIResultObjectCollision({12, 34, 56, 78}),
            ),
        ]
    )
    def test_table(self, name, input_data, expected):
        actual = compute_ci_result(input_data)

        self.assertEqual(actual, expected)
