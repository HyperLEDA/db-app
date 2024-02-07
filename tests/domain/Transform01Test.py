import unittest
from typing import Optional, Union, Callable
from astropy.coordinates import SkyCoord
from pandas import DataFrame

from domain.model.layer0.coordinates import ICRSDescrStr
from domain.model.layer0.values import NoErrorValue
from domain.model.params.cross_identification_param import CrossIdentificationParam
from domain.model.transformation_0_1_stages import ParseCoordinates, ParseValues, CrossIdentification
from domain.usecases import CrossIdentifyUseCase, TransformationO1UseCase
from domain.model import Layer0Model
from domain.model.layer0.layer_0_meta import Layer0Meta
from domain.usecases.exceptions import CrossIdentificationException


class MockedCrossIdentifyUseCase(CrossIdentifyUseCase):
    async def invoke(self, param: CrossIdentificationParam) -> Union[int, CrossIdentificationException]:
        return 0


class PurposefullyFailingCrossIdentifyUseCase(CrossIdentifyUseCase):
    def __init__(self, fail_condition: Callable[[CrossIdentificationParam], bool]):
        self.fail_condition: Callable[[CrossIdentificationParam], bool] = fail_condition

    async def invoke(self, param: CrossIdentificationParam) -> Union[int, CrossIdentificationException]:
        if self.fail_condition(param):
            return CrossIdentificationException(param, [])
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
        self.assertEqual(3, len(models))

    async def test_transform_fails(self):
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
                "speed_col": [1, 2, 3, 4, 5, 6, 7],
                "dist_col": [321, 12, 13124, 324, 42, 1, 4],
                "col_ra": ["00h42.5m", "corrupt", "00h42.5m", "00h42.5m", "00h42.5m", "00h42.5m", "00h42.5m"],
                "col_dec": ["+41d12m", "+41d12m", "+41d12m", "+41d12m", "+41d12m", "corr2", "+41d12m"]
            })
        )

        models, fails = await self.transaction_use_case.invoke(data)
        self.assertEqual(len(fails), 2)
        self.assertEqual(6, fails["speed_col"][1])
        self.assertIsInstance(fails["cause"][0], ValueError)

    async def test_cross_identification_fails(self):
        data = Layer0Model(
            id=1,
            processed=False,
            meta=Layer0Meta(
                value_descriptions=[
                    NoErrorValue("speed;ucd", "speed_col", "km/s"),
                    NoErrorValue("path;ucd", "dist_col", "km")
                ],
                coordinate_descr=ICRSDescrStr("col_ra", "col_dec"),
                nameCol="names_col", dataset=None, comment=None, biblio=None
            ),
            data=DataFrame({
                "speed_col": [1, 2, 3, 4, 5, 6, 7],
                "dist_col": [321, 12, 13124, 324, 42, 1, 4],
                "col_ra": ["00h42.5m", "00h42.5m", "00h42.5m", "00h42.5m", "00h42.5m", "00h42.5m", "00h42.5m"],
                "col_dec": ["+41d12m", "+41d12m", "+41d12m", "+41d12m", "+41d12m", "+41d12m", "+41d12m"],
                "names_col": ["n1", "n2", "fail", "fail2", "n3", "n4", "n"]
            })
        )

        transaction_use_case = TransformationO1UseCase(
            PurposefullyFailingCrossIdentifyUseCase(lambda el: el.name == "fail" or el.name == "fail2")
        )
        models, fails = await transaction_use_case.invoke(data)
        self.assertEqual(len(fails), 2)
        self.assertIsInstance(fails["cause"][0], CrossIdentificationException)
        self.assertIsInstance(fails["cause"][1], CrossIdentificationException)
