import unittest

import structlog
from astropy import units as u
from pandas import DataFrame

from app.data import repositories
from app.domain.actions import logic_units
from app.domain.cross_id_simultaneous_data_provider import PostgreSimultaneousDataProvider
from app.domain.model import Layer0Model
from app.domain.model.layer0.biblio import Biblio
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.params.layer_0_query_param import Layer0QueryParam
from app.lib import testing
from tests.unit.domain.util import noop_cross_identify_function


class SaveAndTransform01(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

        common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        layer0_repo = repositories.Layer0Repository(common_repo, cls.pg_storage.get_storage(), structlog.get_logger())
        tmp_repo = repositories.TmpDataRepositoryImpl(cls.pg_storage.get_storage())

        cls._transformation_depot = logic_units.TransformationO1Depot(
            None,
            noop_cross_identify_function,
            lambda it: PostgreSimultaneousDataProvider(it, tmp_repo),
        )
        cls._transaction_depot = logic_units.Transaction01Depot(cls._transformation_depot)
        cls._layer0_repo: repositories.Layer0Repository = layer0_repo

    def tearDown(self):
        self.pg_storage.clear()

    def test_save_and_transform(self):
        data_from_user = Layer0Model(
            id="test_table_save_and_transform",
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
                biblio=Biblio(None, "2024arXiv240411942G", ["gafsrf"], 1999, "t"),
            ),
            data=DataFrame(
                {
                    "speed_col": [1, 2, 3],
                    "dist_col": [321, 12, 13124],
                    "col_ra": ["00h42.5m", "00h42.5m", "00h42.5m"],
                    "col_dec": ["+41d12m", "+41d12m", "+41d12m"],
                }
            ),
        )

        # store data
        self._layer0_repo.create_instances([data_from_user])

        # get data from database TODO move to usecase
        from_db = self._layer0_repo.fetch_data(Layer0QueryParam())
        got = next(it for it in from_db if it.id == "test_table_save_and_transform")

        raw, transformed, fails = logic_units.transaction_0_1(self._transaction_depot, got)

        self.assertEqual(0, len(fails))
        self.assertEqual(3, len(transformed))

        for t in transformed:
            self.assertEqual("icrs", t.coordinates.frame.name)
            self.assertEqual(u.km / u.s, t.measurements[0].value.unit)
            self.assertEqual("speed;ucd", t.measurements[0].ucd)
            self.assertEqual(u.km, t.measurements[1].value.unit)
            self.assertEqual("path;ucd", t.measurements[1].ucd)
