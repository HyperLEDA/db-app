import unittest
from typing import Optional

from pandas import DataFrame

from app.domain.cross_id_simultaneous_data_provider import SimpleSimultaneousDataProvider
from app.domain.model import Layer0Model, Layer1Model
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.params.layer_0_query_param import Layer0QueryParam
from app.domain.repositories.layer_0_repository import Layer0Repository
from app.domain.repositories.layer_1_repository import Layer1Repository
from app.domain.usecases import TransformationO1UseCase
from app.domain.usecases.transaction_0_1_use_case import Transaction01UseCase
from app.domain.user_interaction.interaction import ResolveCoordinateParseFail
from app.domain.user_interaction.interaction_argument import AbstractArgument
from app.domain.user_interaction.interaction_result import (
    InteractionResult,
    ResolveCoordinateParseFailRes,
)
from tests.domain.util import MockedCrossIdentifyUseCase


class MockedCoordinateParseFailResolver(ResolveCoordinateParseFail):
    async def eval(self, arg: AbstractArgument) -> InteractionResult:
        # user always сancels the data row
        return ResolveCoordinateParseFailRes(True)


class MockedCoordinateParseFailResolverFail(ResolveCoordinateParseFail):
    async def eval(self, arg: AbstractArgument) -> InteractionResult:
        # user always сancels the data row
        return ResolveCoordinateParseFailRes(False)


class MockedCachingLayer0Repo(Layer0Repository):
    async def fetch_data(self, param: Layer0QueryParam) -> list[Layer0Model]:
        return []

    def __init__(self):
        self.last_saved_instances = None

    async def create_update_instances(self, instances: list[Layer0Model]) -> bool:
        self.last_saved_instances = instances
        return True

    async def create_instances(self, instances: list[Layer0Model]):
        """
        Used to create instances, fails on conflict
        :param instances:
        """


class MockedCachingLayer1Repo(Layer1Repository):
    def __init__(self):
        self.last_saved_instances = None

    async def get_by_name(self, name: str) -> Optional[Layer1Model]:
        return None

    async def get_inside_square(
        self, min_ra: float, max_ra: float, min_dec: float, max_dec: float
    ) -> list[Layer1Model]:
        return []

    async def save_update_instances(self, instances: list[Layer1Model]) -> bool:
        self.last_saved_instances = instances
        return True


class Transaction01Test(unittest.IsolatedAsyncioTestCase):
    async def test_transaction_coordinate_fail_0(self):
        """
        Layer 0 data has three rows, one has corrupted coordinates
        """
        data = Layer0Model(
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

        transformation_use_case = TransformationO1UseCase(
            MockedCrossIdentifyUseCase(), lambda it: SimpleSimultaneousDataProvider(it)
        )
        transaction_use_case = Transaction01UseCase(transformation_use_case)
        source, models, fails = await transaction_use_case.invoke(data)
        self.assertEqual(2, len(models))
        self.assertEqual(1, len(fails))
        self.assertEqual(2, fails[0].original_row)
