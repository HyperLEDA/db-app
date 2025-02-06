import unittest
from collections.abc import Hashable
from typing import Any

from astropy import coordinates
from astropy import units as u
from parameterized import param, parameterized

from app import entities
from app.data import model
from app.domain import converters


class CoordinateConverterTest(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "both units are angular",
                [
                    entities.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.ra"),
                    entities.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.dec"),
                ],
            ),
            param(
                "one unit is not angular",
                [
                    entities.ColumnDescription("test", "float", unit=u.joule, ucd="pos.eq.ra"),
                    entities.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.dec"),
                ],
                True,
            ),
            param(
                "one unit is None",
                [
                    entities.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.ra"),
                    entities.ColumnDescription("test", "float", ucd="pos.eq.dec"),
                ],
                True,
            ),
            param(
                "one of coordinates if not present",
                [
                    entities.ColumnDescription("test", "float", unit=u.joule, ucd="pos.eq.ra"),
                ],
                True,
            ),
        ]
    )
    def test_parse_columns(
        self,
        name: str,
        columns: list[entities.ColumnDescription],
        raises: bool = False,
    ):
        converter = converters.ICRSConverter()

        if raises:
            with self.assertRaises(converters.ConverterError):
                converter.parse_columns(columns)
        else:
            converter.parse_columns(columns)

    def test_application(self):
        converter = converters.ICRSConverter()

        converter.parse_columns(
            [
                entities.ColumnDescription("ra", "float", unit=u.hour, ucd="pos.eq.ra"),
                entities.ColumnDescription("dec", "float", unit=u.deg, ucd="pos.eq.dec"),
            ]
        )

        data: dict[Hashable, Any] = {"ra": 10, "dec": 22}
        expected = coordinates.ICRS(10 * u.hour, dec=22 * u.deg)

        actual = converter.apply(data)
        self.assertEqual(actual, model.ICRSCatalogObject(expected.ra.deg, 0.01, expected.dec.deg, 0.01))
