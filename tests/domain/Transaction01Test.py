import unittest
from typing import Union, Optional

from pandas import DataFrame

from domain.model import Layer0Model, Layer1Model
from domain.model.layer0.coordinates import ICRSDescrStr
from domain.model.layer0.layer_0_meta import Layer0Meta
from domain.model.layer0.values import NoErrorValue
from domain.repositories.layer_0_repository import Layer0Repository
from domain.repositories.layer_1_repository import Layer1Repository
from domain.usecases import TransformationO1UseCase
from domain.usecases.transaction_0_1_use_case import Transaction01UseCase
from domain.user_interaction.interaction import ResolveCoordinateParseFail
from domain.user_interaction.interaction_argument import ResolveCoordinateParseFailArg
from domain.user_interaction.interaction_result import InteractionResult, ResolveCoordinateParseFailRes
from tests.domain.Transform01Test import PurposefullyFailingCrossIdentifyUseCase


class MockedCoordinateParseFailResolver(ResolveCoordinateParseFail):
    async def eval(self, arg: ResolveCoordinateParseFailArg) -> InteractionResult:
        # user always сancels the data row
        return ResolveCoordinateParseFailRes(True)


class MockedCoordinateParseFailResolverFail(ResolveCoordinateParseFail):
    async def eval(self, arg: ResolveCoordinateParseFailArg) -> InteractionResult:
        # user always сancels the data row
        return ResolveCoordinateParseFailRes(False)


class MockedCachingLayer0Repo(Layer0Repository):
    def __init__(self):
        self.last_saved_instances = None

    def create_update_instances(self, instances: list[Layer0Model]) -> bool:
        self.last_saved_instances = instances
        return True


class MockedCachingLayer1Repo(Layer1Repository):
    def __init__(self):
        self.last_saved_instances = None

    def get_by_name(self, name: str) -> Optional[Layer1Model]:
        pass

    def get_inside_square(self, min_ra: float, max_ra: float, min_dec: float, max_dec: float) -> list[Layer1Model]:
        pass

    def save_update_instances(self, instances: list[Layer1Model]) -> bool:
        self.last_saved_instances = instances
        return True


class Transaction01Twst(unittest.IsolatedAsyncioTestCase):
    async def test_transaction_coordinate_fail_0(self):
        """
        Test user scenario, when there is three rows, one has corrupted coordinates. User cancels corrupted coordinates
        row, other data is writen to DB
        :return:
        """
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
                "col_dec": ["+41d12m", "+41d12m", "corrupt data"],
            })
        )

        transformation_use_case = TransformationO1UseCase(
            PurposefullyFailingCrossIdentifyUseCase(lambda el: el.name == "fail")
        )
        l0_repo = MockedCachingLayer0Repo()
        l1_repo = MockedCachingLayer1Repo()
        transaction_use_case = Transaction01UseCase(
            transformation_use_case,
            l0_repo,
            l1_repo,
            MockedCoordinateParseFailResolver()
        )
        res = await transaction_use_case.invoke(data)
        self.assertEqual(2, len(res))
        # check, that we updated one level 0 instance
        self.assertEqual(1, len(l0_repo.last_saved_instances))
        # check, that we updated two level 1 instance
        self.assertEqual(2, len(l1_repo.last_saved_instances))

    async def test_transaction_coordinate_fail_1(self):
        """
        Test user scenario, when there is three rows, one has corrupted coordinates. User cancels the whole transaction,
        nothing is writen to the DB
        :return:
        """
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
                "col_dec": ["+41d12m", "+41d12m", "corrupt data"],
            })
        )

        transformation_use_case = TransformationO1UseCase(
            PurposefullyFailingCrossIdentifyUseCase(lambda el: el.name == "fail")
        )
        l0_repo = MockedCachingLayer0Repo()
        l1_repo = MockedCachingLayer1Repo()
        transaction_use_case = Transaction01UseCase(
            transformation_use_case,
            l0_repo,
            l1_repo,
            MockedCoordinateParseFailResolverFail()
        )
        with self.assertRaises(BaseException) as scope:
            res = await transaction_use_case.invoke(data)
        # Coordinate parse fail must result in ValueError
        self.assertIsInstance(scope.exception, ValueError)
