import unittest

from astropy import units as u
from numpy import testing as nptest

from app.domain.unification.modifiers.interface import (
    AddUnitColumnModifier,
    FormatColumnModifier,
    MapColumnModifier,
)


class ModifiersTest(unittest.TestCase):
    def test_add_unit_column_modifier_apply(self):
        modifier = AddUnitColumnModifier("km")
        input_quantity = [1, 2, 3] * u.Unit("km")
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [1, 2, 3] * u.Unit("km"))

    def test_add_unit_column_modifier_apply_with_existing_unit(self):
        modifier = AddUnitColumnModifier("km")
        input_quantity = [1, 2, 3] * u.Unit("m")
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [1, 2, 3] * u.Unit("km"))

    def test_add_unit_column_modifier_apply_with_complex_units(self):
        modifier = AddUnitColumnModifier("J*km/s")
        input_quantity = [1, 2, 3] * u.Unit("m") / u.Unit("s")
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [1, 2, 3] * u.Unit("km") / u.Unit("s") * u.Unit("J"))

    def test_map_column_modifier_apply(self):
        modifier = MapColumnModifier(mapping={1: "one", 2: "two", 3: "three"}, default="unknown")
        input_quantity = [1, 2, 4, 3] * u.dimensionless_unscaled
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, ["one", "two", "unknown", "three"])

    def test_map_column_modifier_with_numeric_values(self):
        modifier = MapColumnModifier(mapping={1: 10, 2: 20, 3: 30}, default=0)
        input_quantity = [1, 2, 4, 3] * u.dimensionless_unscaled
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [10, 20, 0, 30])

    def test_map_column_modifier_with_units(self):
        modifier = MapColumnModifier(mapping={1: 10, 2: 20, 3: 30}, default=0)
        input_quantity = [1, 2, 4, 3] * u.Unit("km")
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [10, 20, 0, 30])

    def test_format_column_modifier_apply(self):
        modifier = FormatColumnModifier("value_{:.0f}")
        input_quantity = [1, 2, 3] * u.dimensionless_unscaled
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, ["value_1", "value_2", "value_3"])

    def test_format_column_modifier_invalid_pattern(self):
        with self.assertRaises(ValueError):
            FormatColumnModifier("too_many_{}_{}")

    def test_format_column_modifier_with_units(self):
        modifier = FormatColumnModifier("value_{:.2f}")
        input_quantity = [1.234, 2.345, 3.456] * u.Unit("km")
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, ["value_1.23", "value_2.35", "value_3.46"])
