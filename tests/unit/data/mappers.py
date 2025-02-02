import unittest

from pandas import DataFrame

from app import entities
from app.data.mappers import data_to_domain, domain_to_data
from app.domain.model import Layer0Model
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.values import NoErrorValue
from app.lib.storage import mapping


class MappersTest(unittest.TestCase):
    def test_layer_0_to_data(self):
        schema = Layer0Model(
            id="1",
            processed=False,
            meta=Layer0Meta(
                value_descriptions=[
                    NoErrorValue("speed;ucd", "speed_col", "km/s"),
                    NoErrorValue("path;ucd", "dist_col", "km"),
                ],
                coordinate_descr=ICRSDescrStr("col_ra", "col_dec"),
                names_descr=None,
                dataset=None,
                comment=None,
                biblio=None,
            ),
            data=DataFrame(
                {
                    "speed_col": [1, 2, 3],
                    "dist_col": [321, 12, 13124],
                    "col_ra": ["00h42.5m", "00h42.5m", "00h42.5m"],
                    "col_dec": ["+41d12m", "+41d12m", "corrupt data"],
                }
            ),
        )

        creation = domain_to_data.layer_0_creation_mapper(schema, 0)
        self.assertEqual(creation.column_descriptions[0].name, schema.meta.value_descriptions[0].column_name)
        self.assertEqual(creation.column_descriptions[0].unit, schema.meta.value_descriptions[0].units)

    def test_layer_0_to_domain(self):
        creation = entities.Layer0Creation(
            "test_name",
            [
                entities.ColumnDescription("col0", mapping.TYPE_TEXT, ucd="fake-ucd"),
                entities.ColumnDescription("col1", mapping.TYPE_DOUBLE_PRECISION, unit="km/s", ucd="fake-ucd"),
            ],
            0,
            None,
            None,
        )
        raw = entities.Layer0RawData(
            0,
            DataFrame(
                {
                    "col0": ["00h42.5m", "00h42.5m", "00h42.5m"],
                    "col1": [321, 12, 13124],
                }
            ),
        )

        bibliography = entities.Bibliography(42, "fake_bibcode", 1999, ["a"], "t")

        model = data_to_domain.layer_0_mapper(creation, raw, bibliography)
        self.assertListEqual(
            [descr.units for descr in model.meta.value_descriptions],
            [descr.unit for descr in creation.column_descriptions],
        )
