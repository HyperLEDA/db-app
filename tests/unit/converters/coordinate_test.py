import unittest
from collections.abc import Hashable
from typing import Any

from astropy import coordinates
from astropy import units as u
from parameterized import param, parameterized

from app.data import model
from app.domain import converters


class CoordinateConverterTest(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "both units are angular",
                [
                    model.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.ra"),
                    model.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.dec"),
                ],
            ),
            param(
                "one unit is not angular",
                [
                    model.ColumnDescription("test", "float", unit=u.joule, ucd="pos.eq.ra"),
                    model.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.dec"),
                ],
                True,
            ),
            param(
                "one unit is None",
                [
                    model.ColumnDescription("test", "float", unit=u.hourangle, ucd="pos.eq.ra"),
                    model.ColumnDescription("test", "float", ucd="pos.eq.dec"),
                ],
                True,
            ),
            param(
                "one of coordinates if not present",
                [
                    model.ColumnDescription("test", "float", unit=u.joule, ucd="pos.eq.ra"),
                ],
                True,
            ),
        ]
    )
    def test_parse_columns(
        self,
        name: str,
        columns: list[model.ColumnDescription],
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
                model.ColumnDescription("ra", "float", unit=u.hour, ucd="pos.eq.ra"),
                model.ColumnDescription("dec", "float", unit=u.deg, ucd="pos.eq.dec"),
            ]
        )

        data: dict[Hashable, Any] = {"ra": 10, "dec": 22}
        expected = coordinates.ICRS(10 * u.hour, dec=22 * u.deg)

        actual = converter.apply(data)
        self.assertEqual(
            actual, model.ICRSCatalogObject(ra=expected.ra.deg, e_ra=0.01, dec=expected.dec.deg, e_dec=0.01)
        )
