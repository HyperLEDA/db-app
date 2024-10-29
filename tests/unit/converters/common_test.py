import unittest

from parameterized import param, parameterized

from app import entities
from app.domain import converters
from app.domain.converters import common


class CommonTest(unittest.TestCase):
    @parameterized.expand(
        [
            param(
                "no correct ucd with None",
                [
                    entities.ColumnDescription("col", "str"),
                    entities.ColumnDescription("col2", "str", ucd="pos.eq.dec"),
                ],
                raises=True,
            ),
            param(
                "no correct ucd",
                [
                    entities.ColumnDescription("col", "str", ucd="pos.eq.ra"),
                    entities.ColumnDescription("col2", "str", ucd="pos.eq.dec"),
                ],
                raises=True,
            ),
            param(
                "single ucd",
                [
                    entities.ColumnDescription("col", "str", ucd="pos.eq.ra"),
                    entities.ColumnDescription("col2", "str", ucd="meta.id"),
                ],
                "col2",
            ),
            param(
                "several UCDs - ambiguous",
                [
                    entities.ColumnDescription("col", "str", ucd="meta.id;meta.main"),
                    entities.ColumnDescription("col2", "str", ucd="meta.id;meta.main"),
                ],
                raises=True,
            ),
            param(
                "several ucds with one main",
                [
                    entities.ColumnDescription("col", "str", ucd="meta.id"),
                    entities.ColumnDescription("col3", "str", ucd="meta.id"),
                    entities.ColumnDescription("col22", "str", ucd="meta.id;meta.main"),
                ],
                "col22",
            ),
        ]
    )
    def test_get_main_column(
        self,
        name: str,
        columns: list[entities.ColumnDescription],
        expected_column_name: str | None = None,
        raises: bool = False,
    ):
        if raises:
            with self.assertRaises(converters.ConverterError):
                _ = common.get_main_column(columns, "meta.id")
        else:
            actual = common.get_main_column(columns, "meta.id")

            self.assertEqual(actual.name, expected_column_name)
