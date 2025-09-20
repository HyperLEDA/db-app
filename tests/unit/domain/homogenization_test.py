import unittest

from astropy import table
from astropy import units as u
from parameterized import param, parameterized

from app.data import model, repositories
from app.domain import homogenization


class HomogenizationTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.table_meta = model.Layer0TableMeta(
            table_name="test_table",
            column_descriptions=[
                model.ColumnDescription(name="ra", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.ra"),
                model.ColumnDescription(name="dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec"),
                model.ColumnDescription(name="e_ra", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.ra;stat.error"),
                model.ColumnDescription(
                    name="e_dec", data_type="float", unit=u.Unit("deg"), ucd="pos.eq.dec;stat.error"
                ),
                model.ColumnDescription(name="name", data_type="text", ucd="meta.id"),
                model.ColumnDescription(name="secondary_name", data_type="text"),
                model.ColumnDescription(name="redshift", data_type="float"),
            ],
            bibliography_id=1,
        )

        self.data = table.Table(
            {
                "ra": [10.0, 20.0] * u.Unit("deg"),
                "dec": [30.0, 40.0] * u.Unit("deg"),
                "e_ra": [0.11, 0.12] * u.Unit("deg"),
                "e_dec": [0.11, 0.12] * u.Unit("deg"),
                "name": ["obj1", "obj2"],
                "secondary_name": ["obj1_s", "obj2_s"],
                "redshift": [0.1, 0.2],
                repositories.INTERNAL_ID_COLUMN_NAME: ["id1", "id2"],
            }
        )

    @parameterized.expand(
        [
            param(
                "simple fill",
                rules=[
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.UCDColumnFilter("meta.id"),
                        priority=1,
                    ),
                ],
                expected_objects=[
                    model.RecordInfo(
                        id="id1",
                        data=[model.DesignationCatalogObject(design="obj1")],
                    ),
                    model.RecordInfo(
                        id="id2",
                        data=[model.DesignationCatalogObject(design="obj2")],
                    ),
                ],
            ),
            param(
                "priority fill",
                rules=[
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.UCDColumnFilter("meta.id"),
                        priority=1,
                    ),
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.ColumnNameColumnFilter("secondary_name"),
                        priority=2,
                    ),
                ],
                expected_objects=[
                    model.RecordInfo(
                        id="id1",
                        data=[model.DesignationCatalogObject(design="obj1_s")],
                    ),
                    model.RecordInfo(
                        id="id2",
                        data=[model.DesignationCatalogObject(design="obj2_s")],
                    ),
                ],
            ),
            param(
                "priority fill but non-passing filter",
                rules=[
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.UCDColumnFilter("meta.id"),
                        priority=1,
                    ),
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.AndColumnFilter(
                            [
                                homogenization.ColumnNameColumnFilter("secondary_name"),
                                homogenization.TableNameColumnFilter("fake_name"),
                            ]
                        ),
                        priority=2,
                    ),
                ],
                expected_objects=[
                    model.RecordInfo(
                        id="id1",
                        data=[model.DesignationCatalogObject(design="obj1")],
                    ),
                    model.RecordInfo(
                        id="id2",
                        data=[model.DesignationCatalogObject(design="obj2")],
                    ),
                ],
            ),
            # param(
            #     "two rules with same priority",
            #     rules=[
            #         homogenization.Rule(
            #             catalog=model.RawCatalog.DESIGNATION,
            #             parameter="design",
            #             filter=homogenization.UCDColumnFilter("meta.id"),
            #         ),
            #         homogenization.Rule(
            #             catalog=model.RawCatalog.DESIGNATION,
            #             parameter="design",
            #             filter=homogenization.ColumnNameColumnFilter("name"),
            #         ),
            #     ],
            #     err_substr="Multiple rules with same priority",
            # ),
            param(
                "no rules satisfy any of the table columns",
                rules=[],
                err_substr="No rules satisfy any of the table columns",
            ),
            param(
                "not enough rules for the catalog object",
                rules=[
                    homogenization.Rule(
                        catalog=model.RawCatalog.ICRS,
                        parameter="ra",
                        filter=homogenization.UCDColumnFilter("pos.eq.ra"),
                    ),
                ],
                expected_objects=[],
            ),
            param(
                "two catalogs",
                rules=[
                    homogenization.Rule(
                        catalog=model.RawCatalog.ICRS,
                        parameter="ra",
                        filter=homogenization.UCDColumnFilter("pos.eq.ra"),
                    ),
                    homogenization.Rule(
                        catalog=model.RawCatalog.ICRS,
                        parameter="dec",
                        filter=homogenization.UCDColumnFilter("pos.eq.dec"),
                    ),
                    homogenization.Rule(
                        catalog=model.RawCatalog.ICRS,
                        parameter="e_ra",
                        filter=homogenization.UCDColumnFilter("pos.eq.ra;stat.error"),
                    ),
                    homogenization.Rule(
                        catalog=model.RawCatalog.ICRS,
                        parameter="e_dec",
                        filter=homogenization.UCDColumnFilter("pos.eq.dec;stat.error"),
                    ),
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.UCDColumnFilter("meta.id"),
                    ),
                ],
                expected_objects=[
                    model.RecordInfo(
                        id="id1",
                        data=[
                            model.ICRSCatalogObject(ra=10.0, dec=30.0, e_ra=0.11, e_dec=0.11),
                            model.DesignationCatalogObject(design="obj1"),
                        ],
                    ),
                    model.RecordInfo(
                        id="id2",
                        data=[
                            model.ICRSCatalogObject(ra=20.0, dec=40.0, e_ra=0.12, e_dec=0.12),
                            model.DesignationCatalogObject(design="obj2"),
                        ],
                    ),
                ],
            ),
            param(
                "two different keys",
                rules=[
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.UCDColumnFilter("meta.id"),
                        key="key1",
                    ),
                    homogenization.Rule(
                        catalog=model.RawCatalog.DESIGNATION,
                        parameter="design",
                        filter=homogenization.ColumnNameColumnFilter("secondary_name"),
                        key="key2",
                    ),
                ],
                expected_objects=[
                    model.RecordInfo(
                        id="id1",
                        data=[
                            model.DesignationCatalogObject(design="obj1"),
                            model.DesignationCatalogObject(design="obj1_s"),
                        ],
                    ),
                    model.RecordInfo(
                        id="id2",
                        data=[
                            model.DesignationCatalogObject(design="obj2"),
                            model.DesignationCatalogObject(design="obj2_s"),
                        ],
                    ),
                ],
            ),
        ]
    )
    def test_table(
        self,
        name: str,
        rules: list[homogenization.Rule],
        params: list[homogenization.Params] | None = None,
        expected_objects: list[model.RecordInfo] | None = None,
        err_substr: str | None = None,
    ):
        h = homogenization.get_homogenization(rules, params or [], self.table_meta)

        if err_substr is not None:
            with self.assertRaises(Exception) as cm:
                objects = h.apply(self.data)
            self.assertIn(err_substr, str(cm.exception))
        else:
            objects = h.apply(self.data)

        if expected_objects is not None:
            self.assertEqual(objects, expected_objects)
