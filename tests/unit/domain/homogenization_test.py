import unittest

import pandas as pd
from astropy import units as u
from parameterized import param, parameterized

from app.data import model, repositories
from app.domain import homogenization


class HomogenizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.table_meta = model.Layer0TableMeta(
            table_name="test_table",
            column_descriptions=[
                model.ColumnDescription(name="ra", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.ra"),
                model.ColumnDescription(name="dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec"),
                model.ColumnDescription(name="name", data_type="text", ucd="meta.id"),
                model.ColumnDescription(name="secondary_name", data_type="text"),
            ],
            bibliography_id=1,
        )

        self.data = pd.DataFrame(
            {
                "ra": [10.0, 20.0],
                "dec": [30.0, 40.0],
                "name": ["obj1", "obj2"],
                "secondary_name": ["obj1_s", "obj2_s"],
                repositories.INTERNAL_ID_COLUMN_NAME: ["id1", "id2"],
            }
        )

    def test_simple_homogenization(self):
        rules = [
            homogenization.Rule(
                catalog="icrs",
                parameter="ra",
                key="coords",
                column_filters=homogenization.UCDColumnFilter("pos.eq.ra"),
                table_filters=homogenization.AndTableFilter([]),
                priority=1,
            ),
            homogenization.Rule(
                catalog="icrs",
                parameter="dec",
                key="coords",
                column_filters=homogenization.UCDColumnFilter("pos.eq.dec"),
                table_filters=homogenization.AndTableFilter([]),
                priority=1,
            ),
            homogenization.Rule(
                catalog="designation",
                parameter="design",
                key="name",
                column_filters=homogenization.UCDColumnFilter("meta.id"),
                table_filters=homogenization.AndTableFilter([]),
                priority=1,
            ),
        ]

        h = homogenization.get_homogenization(rules, [], self.table_meta)
        result = h.apply(self.data)

        self.assertEqual(len(result), 2)

        obj1 = result[0]
        self.assertEqual(obj1.object_id, "id1")
        self.assertEqual(len(obj1.data), 2)

        self.assertEqual(obj1.data[0], model.ICRSCatalogObject(ra=10.0, dec=30.0))
        self.assertEqual(obj1.data[1], model.DesignationCatalogObject(design="obj1"))

        obj2 = result[1]
        self.assertEqual(obj2.object_id, "id2")
        self.assertEqual(len(obj2.data), 2)

        self.assertEqual(obj2.data[0], model.ICRSCatalogObject(ra=20.0, dec=40.0))
        self.assertEqual(obj2.data[1], model.DesignationCatalogObject(design="obj2"))

    def test_priority_rules(self):
        rules = [
            homogenization.Rule(
                catalog="designation",
                parameter="design",
                key="name",
                column_filters=homogenization.UCDColumnFilter("meta.id"),
                table_filters=homogenization.AndTableFilter([]),
                priority=1,
            ),
            homogenization.Rule(
                catalog="designation",
                parameter="design",
                key="name",
                column_filters=homogenization.ColumnNameColumnFilter("secondary_name"),
                table_filters=homogenization.AndTableFilter([]),
                priority=2,
            ),
        ]

        h = homogenization.get_homogenization(rules, [], self.table_meta)
        result = h.apply(self.data)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0].data), 1)
        self.assertEqual(len(result[1].data), 1)
        self.assertEqual(result[0].data[0], model.DesignationCatalogObject(design="obj1_s"))
        self.assertEqual(result[1].data[0], model.DesignationCatalogObject(design="obj2_s"))

    @parameterized.expand(
        [
            param(homogenization.UCDColumnFilter("meta.id"), homogenization.TableNameFilter("test_table"), [1, 1]),
            param(homogenization.UCDColumnFilter("meta.id"), homogenization.ColumnNameColumnFilter("name"), [1, 1]),
            param(
                homogenization.UCDColumnFilter("meta.id"), homogenization.ColumnNameColumnFilter("fake_name"), [0, 0]
            ),
        ]
    )
    def test_filter_combination(self, filter1, filter2, expected_lens):
        rules = [
            homogenization.Rule(
                catalog="designation",
                parameter="design",
                key="name",
                column_filters=homogenization.AndColumnFilter([filter1, filter2]),
                table_filters=homogenization.AndTableFilter([]),
                priority=1,
            )
        ]

        h = homogenization.get_homogenization(rules, [], self.table_meta)
        result = h.apply(self.data)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0].data), expected_lens[0])
        self.assertEqual(len(result[1].data), expected_lens[1])

    def test_keys(self):
        rules = [
            homogenization.Rule(
                catalog="designation",
                parameter="design",
                key="name",
                column_filters=homogenization.UCDColumnFilter("meta.id"),
                table_filters=homogenization.AndTableFilter([]),
                priority=1,
            ),
            homogenization.Rule(
                catalog="designation",
                parameter="design",
                key="name2",
                column_filters=homogenization.ColumnNameColumnFilter("secondary_name"),
                table_filters=homogenization.AndTableFilter([]),
                priority=1,
            ),
            homogenization.Rule(
                catalog="designation",
                parameter="design",
                key="name3",
                column_filters=homogenization.ColumnNameColumnFilter("secondary_name"),
                table_filters=homogenization.TableNameFilter("test_table_fake"),
                priority=3,
            ),
        ]

        h = homogenization.get_homogenization(rules, [], self.table_meta)
        result = h.apply(self.data)

        self.assertEqual(len(result), 2)
        self.assertEqual(len(result[0].data), 2)
        self.assertEqual(len(result[1].data), 2)
        self.assertEqual(result[0].data[0], model.DesignationCatalogObject(design="obj1"))
        self.assertEqual(result[0].data[1], model.DesignationCatalogObject(design="obj1_s"))
        self.assertEqual(result[1].data[0], model.DesignationCatalogObject(design="obj2"))
        self.assertEqual(result[1].data[1], model.DesignationCatalogObject(design="obj2_s"))
