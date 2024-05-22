import unittest

import structlog
from pandas import DataFrame

from app.data import repositories
from app.data.model import Bibliography, ColumnDescription, Layer0Creation, Layer0RawData
from app.data.repositories.layer_0_repository_impl import Layer0RepositoryImpl
from app.domain.model import Layer0Model
from app.domain.model.layer0.biblio import Biblio
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.params.layer_0_query_param import Layer0QueryParam
from app.lib import testing
from app.lib.storage import enums
from app.lib.storage.mapping import TYPE_INTEGER, TYPE_TEXT


class Layer0RepositoryTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = testing.get_test_postgres_storage()

        common_repo = repositories.CommonRepository(cls.pg_storage.get_storage(), structlog.get_logger())
        layer0_repo = repositories.Layer0Repository(cls.pg_storage.get_storage(), structlog.get_logger())

        cls._layer0_repo: repositories.Layer0Repository = layer0_repo
        cls._common_repo: repositories.CommonRepository = common_repo
        cls._layer0_repo_impl: Layer0RepositoryImpl = Layer0RepositoryImpl(layer0_repo, common_repo)

    def tearDown(self):
        self.pg_storage.clear()

    async def test_retrieve(self):
        data = DataFrame({"col0": [1, 2, 3, 4], "col1": ["ad", "ad", "a", "he"]})
        bib_id = self._common_repo.create_bibliography(Bibliography("2024arXiv240411942F", 1999, ["ade"], "title"))
        creation = Layer0Creation(
            "test_table",
            [ColumnDescription("col0", TYPE_INTEGER), ColumnDescription("col1", TYPE_TEXT)],
            bib_id,
            enums.DataType.REGULAR,
        )
        table_id = self._layer0_repo.create_table(creation)
        self._layer0_repo.insert_raw_data(Layer0RawData(table_id, data))

        from_db = await self._layer0_repo_impl.fetch_data(Layer0QueryParam())
        self.assertTrue(data.equals(from_db[0].data))

    async def test_store_retrieve(self):
        expected = Layer0Model(
            id="test_table_store_retrieve",
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
        await self._layer0_repo_impl.create_instances([expected])
        from_db = await self._layer0_repo_impl.fetch_data(Layer0QueryParam())

        got = next(it for it in from_db if it.id == "test_table_store_retrieve")

        self.assertTrue(got.data.equals(expected.data))

        # check coordinate parser
        expected_coord = expected.meta.coordinate_descr.parse_coordinates(expected.data)
        got_coord = got.meta.coordinate_descr.parse_coordinates(got.data)
        self.assertTrue(expected_coord.equals(got_coord))
