import unittest

from astropy import units as u
from numpy import testing as nptest
from parameterized import param, parameterized

from app.domain.unification.modifiers import (
    AddUnitColumnModifier,
    ColumnModifier,
    FormatColumnModifier,
    MapColumnModifier,
)


class ModifiersTest(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "add unit simple",
                modifier=AddUnitColumnModifier("km"),
                input_quantity=[1, 2, 3] * u.Unit("km"),
                expected=[1, 2, 3] * u.Unit("km"),
            ),
            param(
                "add unit with existing unit",
                modifier=AddUnitColumnModifier("km"),
                input_quantity=[1, 2, 3] * u.Unit("m"),
                expected=[1, 2, 3] * u.Unit("km"),
            ),
            param(
                "add unit with complex units",
                modifier=AddUnitColumnModifier("J*km/s"),
                input_quantity=[1, 2, 3] * u.Unit("m") / u.Unit("s"),
                expected=[1, 2, 3] * u.Unit("km") / u.Unit("s") * u.Unit("J"),
            ),
            param(
                "map string values",
                modifier=MapColumnModifier(mapping={1: "one", 2: "two", 3: "three"}, default="unknown"),
                input_quantity=[1, 2, 4, 3] * u.dimensionless_unscaled,
                expected=["one", "two", "unknown", "three"],
            ),
            param(
                "map numeric values",
                modifier=MapColumnModifier(mapping={1: 10, 2: 20, 3: 30}, default=0),
                input_quantity=[1, 2, 4, 3] * u.dimensionless_unscaled,
                expected=[10, 20, 0, 30],
            ),
            param(
                "map with units",
                modifier=MapColumnModifier(mapping={1: 10, 2: 20, 3: 30}, default=0),
                input_quantity=[1, 2, 4, 3] * u.Unit("km"),
                expected=[10, 20, 0, 30],
            ),
            param(
                "format simple",
                modifier=FormatColumnModifier("value_{:.0f}"),
                input_quantity=[1, 2, 3] * u.dimensionless_unscaled,
                expected=["value_1", "value_2", "value_3"],
            ),
            param(
                "format with units",
                modifier=FormatColumnModifier("value_{:.2f}"),
                input_quantity=[1.234, 2.345, 3.456] * u.Unit("km"),
                expected=["value_1.23", "value_2.35", "value_3.46"],
            ),
        ]
    )
    def test_modifiers(self, name: str, modifier: ColumnModifier, input_quantity: u.Quantity, expected: u.Quantity):
        result = modifier.apply(input_quantity)
        nptest.assert_array_equal(result, expected)

    def test_format_column_modifier_invalid_pattern(self):
        with self.assertRaises(ValueError):
            FormatColumnModifier("too_many_{}_{}")
