import unittest

from astropy import units as u
from numpy import testing as nptest

from app.domain.unification.modifiers.interface import AddUnitColumnModifier


class ModifiersTest(unittest.TestCase):
    def test_add_unit_column_modifier_apply(self):
        modifier = AddUnitColumnModifier("km")
        input_quantity = u.Quantity([1, 2, 3])
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [1, 2, 3] * u.km)

    def test_add_unit_column_modifier_apply_with_existing_unit(self):
        modifier = AddUnitColumnModifier("km")
        input_quantity = [1, 2, 3] * u.m
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [1, 2, 3] * u.km)

    def test_add_unit_column_modifier_apply_with_complex_units(self):
        modifier = AddUnitColumnModifier("J*km/s")
        input_quantity = [1, 2, 3] * u.m / u.s
        result = modifier.apply(input_quantity)

        nptest.assert_array_equal(result, [1, 2, 3] * u.km / u.s * u.J)
