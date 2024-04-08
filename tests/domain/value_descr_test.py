import unittest

import astropy.units as u
from pandas import DataFrame

from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.layer0.values.exceptions import ColumnNotFoundException


class ValueDescrTest(unittest.TestCase):
    def test_no_error_value(self):
        df = DataFrame(
            {
                "speed": [1, 2, 3, 4],
            }
        )
        value_descr = NoErrorValue("placeholder", "speed", "km/s")

        speeds = value_descr.parse_values(df)

        # one km/sec == 1000 m/sec
        self.assertEqual(speeds[1].to(u.m / u.s).value, df["speed"][1] * 1000)

    def test_column_not_found(self):
        df = DataFrame(
            {
                "not_speed": [1, 2, 3, 4],
            }
        )
        value_descr = NoErrorValue("placeholder", "speed", "km/s")

        with self.assertRaises(ColumnNotFoundException) as scope:
            value_descr.parse_values(df)
        self.assertEqual(scope.exception.column_names, ["speed"])

    def test_wrong_units(self):
        df = DataFrame(
            {
                "speed": [1, 2, 3, 4],
            }
        )
        value_descr = NoErrorValue("placeholder", "speed", "not units")

        self.assertRaises(ValueError, lambda: value_descr.parse_values(df))
