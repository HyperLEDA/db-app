import unittest
from collections.abc import Callable

from pandas import DataFrame

from app.data import model
from app.data.repositories.layer2_repository import Layer2Repository
from app.domain.cross_id_simultaneous_data_provider import (
    CrossIdSimultaneousDataProvider,
    SimpleSimultaneousDataProvider,
)
from app.domain.model import Layer0Model
from app.domain.model.layer0.coordinates import ICRSDescrStr
from app.domain.model.layer0.layer_0_meta import Layer0Meta
from app.domain.model.layer0.names import SingleColNameDescr
from app.domain.model.layer0.values import NoErrorValue
from app.domain.model.params import cross_identification_result as result
from app.domain.model.params.cross_identification_result import (
    CrossIdentificationCoordCollisionException,
    CrossIdentificationException,
)
from app.domain.model.params.cross_identification_user_param import CrossIdentificationUserParam
from app.domain.model.params.transformation_0_1_stages import (
    CrossIdentification,
    ParseCoordinates,
    ParseValues,
)
from app.domain.usecases import TransformationO1UseCase
from tests.unit.domain.util import noop_cross_identify_function


def get_purposefully_failing_cross_identification_function(
    fail_condition: Callable[[model.Layer0OldObject], bool],
):
    def func(
        layer2_repo: Layer2Repository,
        param: model.Layer0OldObject,
        simultaneous_data_provider: CrossIdSimultaneousDataProvider,
        user_param: CrossIdentificationUserParam,
    ) -> result.CrossIdentifyResult:
        if fail_condition(param):
            return result.CrossIdentifyResult(
                None, CrossIdentificationCoordCollisionException(param.coordinates, None, None, [])
            )
        return result.CrossIdentifyResult(None, None)

    return func


class Transform01Test(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.transformation_use_case = TransformationO1UseCase(
            None, noop_cross_identify_function, lambda it: SimpleSimultaneousDataProvider(it)
        )

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
                    "col_dec": ["+41d12m", "+41d12m", "+41d12m"],
                }
            ),
        )

        stages = []

        models, fails = await self.transformation_use_case.invoke(data, None, stages.append)

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
                names_descr=None,
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
                names_descr=SingleColNameDescr("names_col"),
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

        transformation_use_case = TransformationO1UseCase(
            None,
            get_purposefully_failing_cross_identification_function(lambda el: el.primary_name in {"fail", "fail2"}),
            lambda it: SimpleSimultaneousDataProvider(it),
        )
        res, fails = await transformation_use_case.invoke(data)
        self.assertEqual(len(fails), 2)
        self.assertIsInstance(fails[0].cause, CrossIdentificationException)
        self.assertIsInstance(fails[1].cause, CrossIdentificationException)

    async def test_name_wrong_column_fail(self):
        data = Layer0Model(
            id="1",
            processed=False,
            meta=Layer0Meta(
                value_descriptions=[
                    NoErrorValue("speed;ucd", "speed_col", "km/s"),
                    NoErrorValue("path;ucd", "dist_col", "km"),
                ],
                coordinate_descr=ICRSDescrStr("col_ra", "col_dec"),
                names_descr=SingleColNameDescr("wrong_col"),
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

        with self.assertRaises(KeyError) as scope:
            await self.transformation_use_case.invoke(data)

        self.assertEqual(("wrong_col",), scope.exception.args)
