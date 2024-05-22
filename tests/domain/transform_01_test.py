import unittest
from typing import Callable, Optional, Union

from pandas import DataFrame

from app.domain.model import Layer0Model, Layer1Model
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.params.cross_identification_param import CrossIdentificationParam
from app.domain.model.params.transformation_0_1_stages import (
    CrossIdentification,
    ParseCoordinates,
    ParseValues,
)
from app.domain.repositories.layer_1_repository import Layer1Repository
from app.domain.usecases import CrossIdentifyUseCase, TransformationO1UseCase
from app.domain.usecases.exceptions import CrossIdentificationException


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


class MockedLayer1Repo(Layer1Repository):
    async def make_new_id(self) -> int:
        return 0

    async def get_by_name(self, name: str) -> Optional[Layer1Model]:
        return None

    async def get_inside_square(
        self, min_ra: float, max_ra: float, min_dec: float, max_dec: float
    ) -> list[Layer1Model]:
        return []

    def save_update_instances(self, instances: list[Layer1Model]) -> bool:
        return True


class Transform01Test(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.transformation_use_case = TransformationO1UseCase(MockedCrossIdentifyUseCase(MockedLayer1Repo()))

    async def test_transform_general(self):
        data = Layer0Model(
            id="1",
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
                biblio=None,
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

        stages = []

        models, fails = await self.transformation_use_case.invoke(data, stages.append)

        self.assertEqual(
            [
                ParseCoordinates(),
                ParseValues(),
                CrossIdentification(total=3, progress=1),
                CrossIdentification(total=3, progress=2),
                CrossIdentification(total=3, progress=3),
            ],
            stages,
        )
        self.assertEqual(3, len(models))
        self.assertEqual(0, len(fails))

    async def test_transform_fails(self):
        data = Layer0Model(
            id="1",
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
                biblio=None,
            ),
            data=DataFrame(
                {
                    "speed_col": [1, 2, 3, 4, 5, 6, 7],
                    "dist_col": [321, 12, 13124, 324, 42, 1, 4],
                    "col_ra": [
                        "00h42.5m",
                        "corrupt",
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                    ],
                    "col_dec": [
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                        "corr2",
                        "+41d12m",
                    ],
                }
            ),
        )

        _, fails = await self.transformation_use_case.invoke(data)
        self.assertEqual(len(fails), 2)
        self.assertEqual(5, fails[1].original_row)
        self.assertIsInstance(fails[0].cause, ValueError)

    async def test_cross_identification_fails(self):
        data = Layer0Model(
            id="1",
            processed=False,
            meta=Layer0Meta(
                value_descriptions=[
                    NoErrorValue("speed;ucd", "speed_col", "km/s"),
                    NoErrorValue("path;ucd", "dist_col", "km"),
                ],
                coordinate_descr=ICRSDescrStr("col_ra", "col_dec"),
                name_col="names_col",
                dataset=None,
                comment=None,
                biblio=None,
            ),
            data=DataFrame(
                {
                    "speed_col": [1, 2, 3, 4, 5, 6, 7],
                    "dist_col": [321, 12, 13124, 324, 42, 1, 4],
                    "col_ra": [
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                        "00h42.5m",
                    ],
                    "col_dec": [
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                        "+41d12m",
                    ],
                    "names_col": ["n1", "n2", "fail", "fail2", "n3", "n4", "n"],
                }
            ),
        )

        transaction_use_case = TransformationO1UseCase(
            PurposefullyFailingCrossIdentifyUseCase(lambda el: el.name in {"fail", "fail2"})
        )
        _, fails = await transaction_use_case.invoke(data)
        self.assertEqual(len(fails), 2)
        self.assertIsInstance(fails[0].cause, CrossIdentificationException)
        self.assertIsInstance(fails[1].cause, CrossIdentificationException)
