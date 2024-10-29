import unittest

import structlog
from astropy.coordinates import SkyCoord
from pandas import DataFrame

from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.values.exceptions import ColumnNotFoundException

logger: structlog.stdlib.BoundLogger = structlog.get_logger()


class ICRSDescrDescrTest(unittest.TestCase):
    def setUp(self):
        self._data_examples_single = [
            "J000055.99+202017.1",
            "00:00:55.99 +20:20:17.1",
            "182.767746 +50.484854",
            "B123456.1-201256",
            "09h 34m 24.7s +12d 45' 34\"",
            "01 23 45.67 -12 34 56.7",
            "00h42.5m +41d12m",
        ]
        self._data_examples_double = [
            ["J000055.99", "+202017.1"],
            "00:00:55.99",
            "+20:20:17.1",
            "182.767746",
            "+50.484854",
            "B123456.1",
            "-201256",
            "09h 34m 24.7s",
            "+12d 45' 34\"",
            "01 23 45.67",
            "-12 34 56.7",
            ["00h42.5m", "+41d12m"],
        ]

    def test_wrong_columns(self):
        cd = ICRSDescrStr("col11", "col22", "col1")
        df = DataFrame({"col1": self._data_examples_single, "col2": self._data_examples_single})
        with self.assertRaises(ColumnNotFoundException) as scope:
            cd.parse_coordinates(df)

        self.assertEqual(2, len(scope.exception.column_names))
        self.assertTrue("col11" in scope.exception.column_names)
        self.assertTrue("col22" in scope.exception.column_names)

    def test_parsing_errors(self):
        cd = ICRSDescrStr("col0")
        df = DataFrame({"col0": ["09h 34m 24.7s +12d 45' 34\"", "very corrupt data"]})

        coordinates = cd.parse_coordinates(df)
        self.assertIsInstance(coordinates[0], SkyCoord)
        self.assertIsInstance(coordinates[1], ValueError)

    def test_coordinates_one_col(self):
        cd = ICRSDescrStr("col1")
        df = DataFrame({"col1": self._data_examples_single})
        coords = cd.parse_coordinates(df)
        logger.info(coords)

    def test_coordinates_two_col(self):
        cd = ICRSDescrStr("col1", "col2")
        df = DataFrame(
            {
                "col1": [x[0] for x in self._data_examples_double],
                "col2": [x[1] for x in self._data_examples_double],
            }
        )
        coords = cd.parse_coordinates(df)
        logger.info(coords)
