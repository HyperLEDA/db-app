import unittest

import structlog
from astropy import units as u
from pandas import DataFrame

from app.data import repositories
from app.data.repositories.layer_0_repository_impl import Layer0RepositoryImpl
from app.domain import usecases
from app.domain.model import Layer0Model
from app.domain.model.layer0.biblio import Biblio
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.params.layer_0_query_param import Layer0QueryParam
from app.lib import testing


class MockedCrossIdentifyUseCase(usecases.CrossIdentifyUseCase):
    def __init__(self):
        super().__init__(None)

    async def invoke(self, param):
        return 0


class SaveAndTransform01(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

        common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        layer0_repo_impl = Layer0RepositoryImpl(layer0_repo, common_repo)
        transformation_use_case = usecases.TransformationO1UseCase(MockedCrossIdentifyUseCase())
        cls._transaction_use_case: usecases.Transaction01UseCase = usecases.Transaction01UseCase(
            transformation_use_case
        )
        cls._store_l0_use_case: usecases.StoreL0UseCase = usecases.StoreL0UseCase(layer0_repo_impl)
        cls._layer0_repo: repositories.Layer0Repository = layer0_repo
        cls._layer0_repo_impl: Layer0RepositoryImpl = layer0_repo_impl

    def tearDown(self):
        self.pg_storage.clear()

    async def test_save_and_transform(self):
        data_from_user = Layer0Model(
            id="test_table_save_and_transform",
            processed=False,
            meta=Layer0Meta(
                value_descriptions=[
                    NoErrorValue("speed;ucd", "speed_col", "km/s"),
                    NoErrorValue("path;ucd", "dist_col", "km"),
                ],
                coordinate_descr=ICRSDescrStr("col_ra", "col_dec"),
                name_col=None,
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
        await self._store_l0_use_case.invoke([data_from_user])

        # get data from database TODO move to usecase
        from_db = await self._layer0_repo_impl.fetch_data(Layer0QueryParam())
        got = next(it for it in from_db if it.id == "test_table_save_and_transform")

        raw, transformed, fails = await self._transaction_use_case.invoke(got)

        self.assertEqual(0, len(fails))
        self.assertEqual(3, len(transformed))

        for t in transformed:
            self.assertEqual("icrs", t.coordinates.frame.name)
            self.assertEqual(u.km / u.s, t.measurements[0].value.unit)
            self.assertEqual("speed;ucd", t.measurements[0].ucd)
            self.assertEqual(u.km, t.measurements[1].value.unit)
            self.assertEqual("path;ucd", t.measurements[1].ucd)
