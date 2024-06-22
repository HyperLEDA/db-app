import unittest
from uuid import uuid4

import astropy.units as u
from astropy.coordinates import ICRS, angular_separation

from app.domain.cross_id_simultaneous_data_provider import SimpleSimultaneousDataProvider
from app.domain.model.layer2 import Layer2Model
from app.domain.model.params import CrossIdentificationParam
from app.domain.model.params.cross_dentification_user_param import CrossIdentificationUserParam
from app.domain.model.params.cross_identification_result import (
    CrossIdentificationCoordCollisionException,
    CrossIdentificationDuplicateException,
    CrossIdentificationNameCoordCollisionException,
    CrossIdentificationNameCoordCoordException,
    CrossIdentificationNameCoordFailException,
    CrossIdentifySuccess,
)
from app.domain.model.params.layer_2_query_param import Layer2QueryByName, Layer2QueryInCircle, Layer2QueryParam
from app.domain.repositories.layer_2_repository import Layer2Repository
from app.domain.usecases import CrossIdentifyUseCase
from app.domain.usecases.cross_identify_use_case import default_r1
from tests.domain.util import make_points


class MockedLayer2Repository(Layer2Repository):
    def __init__(self, data: list[Layer2Model]):
        self._data = data

    async def query_data(self, param: Layer2QueryParam) -> list[Layer2Model]:
        if isinstance(param, Layer2QueryByName):
            return [it for it in self._data if it.name == param.name]

        if isinstance(param, Layer2QueryInCircle):
            return [
                it
                for it in self._data
                if angular_separation(it.coordinates.ra, it.coordinates.dec, param.center.ra, param.center.dec)
                <= param.r
            ]

        raise ValueError(f"Unknown param type: {type(param)}")

    async def save_update_instances(self, instances: list[Layer2Model]):
        pass


def _make_l2(pgc: int, coord: ICRS | None, name: str | None) -> Layer2Model:
    return Layer2Model(
        pgc,
        coord,
        name,
        0 * u.rad,
        0 * u.rad,
        0,
    )


class CrossIdentifyTest(unittest.IsolatedAsyncioTestCase):
    async def test_identify_coord_new_object(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = CrossIdentificationParam(None, center)

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc + [target])

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, None) for i, it in enumerate(outside)])

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(target, data_provider, CrossIdentificationUserParam(None, None))

        self.assertIsInstance(res, CrossIdentifySuccess, "Cross identification must pass")
        self.assertEqual(res.result, None)

    async def test_identify_in_default_r(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = ICRS(ra=center.ra + default_r1 / 2, dec=center.dec)
        target_id = 256

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, None) for i, it in enumerate(outside)] + [_make_l2(target_id, target, None)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(None, center), data_provider, CrossIdentificationUserParam(None, None)
        )

        self.assertIsInstance(res, CrossIdentifySuccess, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    async def test_identify_in_custom_r(self):
        r1 = 5 * u.deg
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = ICRS(ra=center.ra + r1 / 2, dec=center.dec)
        target_id = 256

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, None) for i, it in enumerate(outside)] + [_make_l2(target_id, target, None)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(None, center), data_provider, CrossIdentificationUserParam(r1, 1.1 * r1)
        )

        self.assertIsInstance(res, CrossIdentifySuccess, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    async def test_identify_coord_fail(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + default_r1 / 2, dec=center.dec)
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + default_r1 / 2)
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, None) for i, it in enumerate(outside)]
            + [_make_l2(target1_id, target1, None), _make_l2(target2_id, target2, None)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(None, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        if not isinstance(res, CrossIdentificationCoordCollisionException):
            self.fail("Cross identification must fail with 'CrossIdentificationCoordCollisionException'")

    async def test_identify_by_name(self):
        target = uuid4().hex
        target_id = 256

        all_pts, _ = make_points(n_points=100, center=ICRS(ra=20 * u.deg, dec=40 * u.deg), r=10 * u.deg)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(all_pts[:-1])]
            + [_make_l2(target_id, all_pts[-1].coordinates, target)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(target, None),
            SimpleSimultaneousDataProvider([CrossIdentificationParam(uuid4().hex, None) for _ in range(20)]),
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsInstance(res, CrossIdentifySuccess, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    async def test_identify_by_name_new_object(self):
        all_pts, _ = make_points(n_points=100, center=ICRS(ra=20 * u.deg, dec=40 * u.deg), r=10 * u.deg)

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(all_pts[:-1])])

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(uuid4().hex, None),
            SimpleSimultaneousDataProvider([CrossIdentificationParam(uuid4().hex, None) for _ in range(20)]),
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsInstance(res, CrossIdentifySuccess, "Cross identification must pass")
        self.assertEqual(res.result, None)

    @unittest.skip("No fail case for name identification")
    async def test_identify_by_name_fail(self):
        pass

    async def test_identify_by_name_and_coordinates(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = ICRS(ra=center.ra + default_r1 / 2, dec=center.dec)
        target_name = uuid4().hex
        target_id = 256

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(outside)]
            + [_make_l2(target_id, target, target_name)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(target_name, center), data_provider, CrossIdentificationUserParam(None, None)
        )

        self.assertIsInstance(res, CrossIdentifySuccess, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    async def test_identify_by_name_and_coordinates_new_object(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [
            CrossIdentificationParam(uuid4().hex, it.coordinates) for it in all_pts if it not in inside_proc
        ]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(outside)])

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(uuid4().hex, center), data_provider, CrossIdentificationUserParam(None, None)
        )

        self.assertIsInstance(res, CrossIdentifySuccess, "Cross identification must pass")
        self.assertEqual(res.result, None)

    async def test_name_coord_collision(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + default_r1 / 2, dec=center.dec)
        target1_name = uuid4().hex
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + default_r1 * 30)
        target2_name = uuid4().hex
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(outside)]
            + [_make_l2(target1_id, target1, target1_name), _make_l2(target2_id, target2, target2_name)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(target2_name, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        self.assertIsInstance(
            res,
            CrossIdentificationNameCoordCollisionException,
            "Cross identification must fail with 'CrossIdentificationNameCoordCollisionException'",
        )

    @unittest.skip("No fail case for name identification")
    async def test_name_coord_fail(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + default_r1 / 2, dec=center.dec)
        target1_name = uuid4().hex
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + default_r1 / 2)
        target2_name = uuid4().hex
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(outside)]
            + [_make_l2(target1_id, target1, target1_name), _make_l2(target2_id, target2, target2_name)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(target2_name, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        self.assertIsInstance(
            res,
            CrossIdentificationNameCoordFailException,
            "Cross identification must fail with 'CrossIdentificationNameCoordFailException'",
        )

    @unittest.skip("No fail case for name identification")
    async def test_name_coord_fail_name(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + default_r1 / 2, dec=center.dec)
        target1_name = uuid4().hex
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + default_r1 / 2)
        target2_name = uuid4().hex
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(outside)]
            + [_make_l2(target1_id, target1, target1_name), _make_l2(target2_id, target2, target2_name)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(target2_name, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        self.assertIsInstance(
            res,
            CrossIdentificationNameCoordFailException,
            "Cross identification must fail with 'CrossIdentificationNameCoordFailException'",
        )

    async def test_name_coord_fail_coord(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + default_r1 / 2, dec=center.dec)
        target1_name = uuid4().hex
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + default_r1 / 2)
        target2_name = uuid4().hex
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, uuid4().hex) for i, it in enumerate(outside)]
            + [_make_l2(target1_id, target1, target1_name), _make_l2(target2_id, target2, target2_name)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(target2_name, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        if isinstance(res, CrossIdentificationNameCoordCoordException):
            self.assertEqual(res.name_hit.pgc, target2_id)
        else:
            self.fail("Cross identification must fail with 'CrossIdentificationNameCoordCoordException'")

    @unittest.skip("Name data model incomplete")
    async def test_simultaneous_name_fail(self):
        pass

    async def test_simultaneous_coord_fail(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = CrossIdentificationParam(None, ICRS(ra=center.ra + default_r1 / 2, dec=center.dec))
        target2 = CrossIdentificationParam(None, ICRS(ra=center.ra, dec=center.dec + default_r1 / 2))

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc + [target1, target2])

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, None) for i, it in enumerate(outside)])

        use_case = CrossIdentifyUseCase(repo)

        res = await use_case.invoke(
            CrossIdentificationParam(None, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        self.assertIsInstance(res, CrossIdentificationDuplicateException)
        self.assertIsInstance(res.db_cross_id_result, CrossIdentifySuccess)
        self.assertTrue(target1 in res.collisions)
        self.assertTrue(target2 in res.collisions)
