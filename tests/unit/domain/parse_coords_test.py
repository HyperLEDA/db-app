import unittest

import astropy.units as u
from astropy import coordinates as coords
from parameterized import param, parameterized

from app.data.repositories import layer2
from app.domain.dataapi.search_parsers import (
    HMSDMSCoordinateParser,
    JCoordinateParser,
    _parse_j_coord_to_skycoord,
)


class TestJCoordinateParser(unittest.TestCase):
    def setUp(self):
        self.parser = JCoordinateParser()

    @parameterized.expand(
        [
            param(
                "J123456+123456",
                coords.SkyCoord(
                    "12:34:56 +12:34:56",
                    unit=(u.Unit("hourangle"), u.Unit("deg")),
                ),
            ),
            param(
                "J001122.33+443322.1",
                coords.SkyCoord(
                    "00:11:22.33 +44:33:22.1",
                    unit=(u.Unit("hourangle"), u.Unit("deg")),
                ),
            ),
            param(
                "j001122+443322",
                coords.SkyCoord(
                    "00:11:22 +44:33:22",
                    unit=(u.Unit("hourangle"), u.Unit("deg")),
                ),
            ),
        ]
    )
    def test_accepts_valid_j_format(self, input_str, expected):
        result = self.parser.parse(input_str)
        assert result is not None
        filter_obj, search_params = result
        assert isinstance(filter_obj, layer2.ICRSCoordinatesInRadiusFilter)
        assert isinstance(search_params, layer2.ICRSSearchParams)
        assert search_params.get_params()["ra"] == expected.ra.deg
        assert search_params.get_params()["dec"] == expected.dec.deg

    @parameterized.expand(
        [
            "M33",
            "12h30m49s+12d22m33s",
            "J12:34:56+12:34:56",
            "J123",
            "J12345+123",
        ]
    )
    def test_rejects_invalid(self, input_str):
        result = self.parser.parse(input_str)
        assert result is None


class TestJCoordToSkyCoord(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "J001122.33+443322.1",
                coords.SkyCoord(
                    "00:11:22.33 +44:33:22.1",
                    unit=(u.Unit("hourangle"), u.Unit("deg")),
                ),
            ),
        ]
    )
    def test_parsed_coordinates_match(self, input_str, expected):
        result = _parse_j_coord_to_skycoord(input_str)
        assert isinstance(result, coords.SkyCoord)
        assert abs(result.ra.deg - expected.ra.deg) < 1e-5
        assert abs(result.dec.deg - expected.dec.deg) < 1e-5

    def test_invalid_raises(self):
        try:
            _parse_j_coord_to_skycoord("not-j-format")
            raise AssertionError("expected ValueError")
        except ValueError:
            pass


class TestHMSDMSCoordinateParser(unittest.TestCase):
    def setUp(self):
        self.parser = HMSDMSCoordinateParser()

    @parameterized.expand(
        [
            param(
                "12h32m22s+15d22m45s",
                coords.SkyCoord(
                    "12:32:22 +15:22:45",
                    unit=(u.Unit("hourangle"), u.Unit("deg")),
                ),
            ),
            param(
                "12h30m49.32s+12d22m33.2s",
                coords.SkyCoord(
                    "12:30:49.32 +12:22:33.2",
                    unit=(u.Unit("hourangle"), u.Unit("deg")),
                ),
            ),
        ]
    )
    def test_accepts_valid_hms_dms_format(self, input_str, expected):
        result = self.parser.parse(input_str)
        assert result is not None
        filter_obj, search_params = result
        assert isinstance(filter_obj, layer2.ICRSCoordinatesInRadiusFilter)
        assert isinstance(search_params, layer2.ICRSSearchParams)
        assert abs(search_params.get_params()["ra"] - expected.ra.deg) < 1e-5
        assert abs(search_params.get_params()["dec"] - expected.dec.deg) < 1e-5

    @parameterized.expand(
        [
            "M33",
            "J123049.32+122233.2",
            "12:30:49 +12:22:33",
            "12h30m49s",
            "invalid",
        ]
    )
    def test_rejects_invalid(self, input_str):
        result = self.parser.parse(input_str)
        assert result is None
