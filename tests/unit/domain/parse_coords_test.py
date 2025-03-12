import unittest

import astropy.units as u
from astropy import coordinates as coords
from parameterized import param, parameterized

from app.domain.dataapi.actions import parse_coordinates


class TestParseCoordinates(unittest.TestCase):
    def setUp(self):
        pass

    @parameterized.expand(
        [
            param("J12:34:56+12:34:56", coords.SkyCoord("12:34:56 +12:34:56", unit=(u.hourangle, u.deg))),
            param("B12:34:56-12:34:56", coords.SkyCoord("12:34:56 -12:34:56", unit=(u.hourangle, u.deg))),
            param(
                "G180.5+45.8", coords.SkyCoord(l=180.5 * u.deg, b=45.8 * u.deg, frame="galactic").transform_to("icrs")
            ),
            param("12:34:56 +12:34:56", coords.SkyCoord("12:34:56 +12:34:56", unit=(u.hourangle, u.deg))),
        ]
    )
    def test_valid_coordinates(self, input_str, expected):
        result = parse_coordinates(input_str)
        self.assertIsInstance(result, coords.SkyCoord)
        self.assertEqual(result.ra.deg, expected.ra.deg)
        self.assertEqual(result.dec.deg, expected.dec.deg)

    @parameterized.expand(["invalid", "J12:34", "G180", "X12:34:56 +12:34:56"])
    def test_invalid_coordinates(self, input_str):
        with self.assertRaisesRegex(ValueError, "Invalid coordinate format"):
            parse_coordinates(input_str)


if __name__ == "__main__":
    unittest.main()
