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
from tests.domain.Transform01Test import PurposefullyFailingCrossIdentifyUseCase, MockedCrossIdentifyUseCase


class MockedCoordinateParseFailResolverFail(ResolveCoordinateParseFail):
    async def eval(self, arg: ResolveCoordinateParseFailArg) -> InteractionResult:
        # user always сancels the data row
        return ResolveCoordinateParseFailRes(False)


class MockedLayer1Repo(Layer1Repository):
    async def make_new_id(self) -> int:
        return 0

    def get_by_name(self, name: str) -> Optional[Layer1Model]:
        pass

    def get_inside_square(self, min_ra: float, max_ra: float, min_dec: float, max_dec: float) -> list[Layer1Model]:
        pass

    def save_update_instances(self, instances: list[Layer1Model]) -> bool:
        return True


class Transaction01Twst(unittest.IsolatedAsyncioTestCase):
    async def test_transaction_coordinate_fail_0(self):
        """
        Layer 0 data has three rows, one has corrupted coordinates
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

        transformation_use_case = TransformationO1UseCase(MockedCrossIdentifyUseCase(MockedLayer1Repo()))
        transaction_use_case = Transaction01UseCase(transformation_use_case)
        source, models, fails = await transaction_use_case.invoke(data)
        self.assertEqual(2, len(models))
        self.assertEqual(1, len(fails))
        self.assertEqual(2, fails[0].original_row)
