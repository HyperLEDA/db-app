import unittest
from typing import Optional
from astropy.coordinates import SkyCoord
from pandas import DataFrame

from domain.model.layer0.coordinates import ICRSDescrStr
from domain.model.layer0.values import NoErrorValue
from domain.model.transformation_0_1_stages import ParseCoordinates, ParseValues, CrossIdentification
from domain.usecases import CrossIdentifyUseCase, TransformationO1UseCase
from domain.model import Layer0Model
from domain.model.layer0.layer_0_meta import Layer0Meta


class MockedCrossIdentifyUseCase(CrossIdentifyUseCase):
    async def invoke(self, name: Optional[str], coordinates: Optional[SkyCoord]) -> int:
        return 0


class Transform01Test(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.transaction_use_case = TransformationO1UseCase(MockedCrossIdentifyUseCase())

    async def test_transform_general(self):
        data = Layer0Model(
            id=1,
            processed=False,
            meta=Layer0Meta(
                value_descriptions=[
                    NoErrorValue("speed;ucd", "speed_col", "km/s"),
                    NoErrorValue("path;ucd", "dist_col", "km")
                ],
                coordinate_descr=ICRSDescrStr("col_ra", "col_dec"),
                nameCol=None, dataset=None, comment=None, biblio=None
            ),
            data=DataFrame({
                "speed_col": [1, 2, 3],
                "dist_col": [321, 12, 13124],
                "col_ra": ["00h42.5m", "00h42.5m", "00h42.5m"],
                "col_dec": ["+41d12m", "+41d12m", "+41d12m"]
            })
        )

        stages = []

        models, fails = await self.transaction_use_case.invoke(data, lambda stage: stages.append(stage))

        self.assertEqual([
            ParseCoordinates(),
            ParseValues(),
            CrossIdentification(total=3, progress=1),
            CrossIdentification(total=3, progress=2),
            CrossIdentification(total=3, progress=3)
        ], stages)

