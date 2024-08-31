import unittest

import numpy as np
import pandas
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
        converter = converters.CoordinateConverter("pos.eq.ra")

        if raises:
            with self.assertRaises(converters.ConverterError):
                converter.parse_columns([entities.ColumnDescription("test", "str", unit=unit, ucd="pos.eq.ra")])
        else:
            converter.parse_columns([entities.ColumnDescription("test", "str", unit=unit, ucd="pos.eq.ra")])

    @parameterized.expand(
        [
            param("empty array", np.array([]), u.Quantity([])),
            param(
                "non-empty array",
                np.array([10, 11, 12]),
                u.Quantity([10, 11, 12], u.hourangle),
            ),
        ]
    )
    def test_conversion(self, name: str, input_column: list[NDArray], expected: u.Quantity):
        converter = converters.CoordinateConverter("pos.eq.ra")

        converter.parse_columns(
            [
                entities.ColumnDescription("test", "float", unit=u.hour, ucd="pos.eq.ra"),
                entities.ColumnDescription("test2", "str", ucd="meta.id"),
            ]
        )

        actual = converter.convert(
            pandas.DataFrame(
                {
                    "test": input_column,
                    "test2": ["a"] * len(input_column),
                }
            )
        )

        np.testing.assert_equal(actual, expected)
