import unittest

import numpy as np
from astropy import units as u
from numpy.typing import NDArray
from parameterized import param, parameterized

from app import entities
from app.domain import converters


class CoordinateConverterTest(unittest.TestCase):
    @parameterized.expand(
        [
            param("unit is angular", u.hourangle),
            param("unit is None", None, True),
            param("unit is not angular", u.meter, True),
        ],
    )
    def test_constructor_units(self, name: str, unit: u.Unit | None, raises: bool = False):
        if raises:
            with self.assertRaises(converters.ConverterError):
                converters.CoordinateConverter(entities.ColumnDescription("test", "str", unit=unit))
        else:
            _ = converters.CoordinateConverter(entities.ColumnDescription("test", "str", unit=unit))

    @parameterized.expand(
        [
            param("empty array", [np.array([])], u.Quantity([])),
            param(
                "non-empty array",
                [np.array([10, 11, 12])],
                u.Quantity([10, 11, 12], u.hourangle),
            ),
        ]
    )
    def test_conversion(self, name: str, input_columns: list[NDArray], expected: u.Quantity):
        converter = converters.CoordinateConverter(entities.ColumnDescription("test", "str", unit=u.hour))

        actual = converter.convert(input_columns)

        np.testing.assert_equal(actual, expected)
