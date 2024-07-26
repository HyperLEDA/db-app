import unittest
from uuid import uuid4

import astropy.units as u
from astropy.coordinates import ICRS, angular_separation

from app.domain.cross_id_simultaneous_data_provider import SimpleSimultaneousDataProvider
from app.domain.model.layer2 import Layer2Model
from app.domain.model.params import CrossIdentificationParam
from app.domain.model.params.cross_identification_result import (
    CrossIdentificationCoordCollisionException,
    CrossIdentificationDuplicateException,
    CrossIdentificationNameCoordCollisionException,
    CrossIdentificationNameCoordCoordException,
    CrossIdentificationNameCoordFailException,
    CrossIdentificationNameCoordNameFailException,
    CrossIdentificationNamesDuplicateException,
    CrossIdentificationNamesNotFoundException,
    CrossIdentifyResult,
)
from app.domain.model.params.cross_identification_user_param import CrossIdentificationUserParam
from app.domain.model.params.layer_2_query_param import Layer2QueryByNames, Layer2QueryInCircle, Layer2QueryParam
from app.domain.repositories.layer_2_repository import Layer2Repository
from app.domain.usecases import CrossIdentifyUseCase
from app.domain.usecases.cross_identify_use_case import INNER_RADIUS
from tests.domain.util import make_points


class MockedLayer2Repository(Layer2Repository):
    def __init__(self, data: list[Layer2Model]):
        self._data = data

    def query_data(self, param: Layer2QueryParam) -> list[Layer2Model]:
        if isinstance(param, Layer2QueryByNames):
            names_set = set(param.names)
            return [it for it in self._data if len(set(it.names) & names_set) > 0]

        if isinstance(param, Layer2QueryInCircle):
            return [
                it
                for it in self._data
                if angular_separation(it.coordinates.ra, it.coordinates.dec, param.center.ra, param.center.dec)
                <= param.r
            ]

        raise ValueError(f"Unknown param type: {type(param)}")

    def save_update_instances(self, instances: list[Layer2Model]):
        pass


def _make_l2(pgc: int, coord: ICRS | None, names: list[str] | None, common_name: str | None) -> Layer2Model:
    return Layer2Model(
        pgc,
        coord,
        names if names is not None else [],
        common_name,
        0 * u.rad,
        0 * u.rad,
        0,
    )


def _make_names(n_names: int) -> tuple[list[str], str]:
    """
    :param n_names: Number of names to generate
    :return: all_names, common_name
    """
    all_names = [uuid4().hex for _ in range(n_names)]
    return all_names, all_names[0]


class CrossIdentifyTest(unittest.TestCase):
    def test_identify_coord_new_object(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = CrossIdentificationParam(None, None, center)

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc + [target])

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, None, None) for i, it in enumerate(outside)])

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(target, data_provider, CrossIdentificationUserParam(None, None))

        self.assertIsNone(res.fail, "Cross identification must pass")
        self.assertEqual(res.result, None)

    def test_identify_in_default_r(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec)
        target_id = 256

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, None, None) for i, it in enumerate(outside)]
            + [_make_l2(target_id, target, None, None)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam(None, None, center), data_provider, CrossIdentificationUserParam(None, None)
        )

        self.assertIsNone(res.fail, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    def test_identify_in_custom_r(self):
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
            [_make_l2(i, it.coordinates, None, None) for i, it in enumerate(outside)]
            + [_make_l2(target_id, target, None, None)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam(None, None, center), data_provider, CrossIdentificationUserParam(r1, 1.1 * r1)
        )

        self.assertIsNone(res.fail, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    def test_identify_coord_fail(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec)
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + INNER_RADIUS / 2)
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, None, None) for i, it in enumerate(outside)]
            + [_make_l2(target1_id, target1, None, None), _make_l2(target2_id, target2, None, None)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam(None, None, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        self.assertIsInstance(
            res.fail,
            CrossIdentificationCoordCollisionException,
            "Cross identification must fail with 'CrossIdentificationCoordCollisionException'",
        )

    def test_identify_by_name(self):
        target_names = [uuid4().hex, uuid4().hex, uuid4().hex]
        target_id = 256

        all_pts, _ = make_points(n_points=100, center=ICRS(ra=20 * u.deg, dec=40 * u.deg), r=10 * u.deg)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, *_make_names(3)) for i, it in enumerate(all_pts[:-1])]
            + [_make_l2(target_id, all_pts[-1].coordinates, target_names, target_names[0])]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam(target_names[:1], target_names[0], None),
            SimpleSimultaneousDataProvider([CrossIdentificationParam(*_make_names(1), None) for _ in range(20)]),
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsNone(res.fail, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    def test_identify_by_name_unfounded(self):
        """When whe hane only names, and no matches in DB, we need user decision"""
        all_pts, _ = make_points(n_points=100, center=ICRS(ra=20 * u.deg, dec=40 * u.deg), r=10 * u.deg)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, *_make_names(3)) for i, it in enumerate(all_pts[:-1])]
        )

        use_case = CrossIdentifyUseCase(repo)

        all_names, name = _make_names(1)
        res = use_case.invoke(
            CrossIdentificationParam(all_names, name, None),
            SimpleSimultaneousDataProvider([CrossIdentificationParam(*_make_names(1), None) for _ in range(20)]),
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsInstance(res.fail, CrossIdentificationNamesNotFoundException)
        self.assertEqual(res.fail.names, all_names)

    def test_identify_by_name_duplicate(self):
        """Case, when provided names found for multiple objects in DB"""
        all_pts, _ = make_points(n_points=100, center=ICRS(ra=20 * u.deg, dec=40 * u.deg), r=10 * u.deg)

        all_in_repo = [_make_l2(i, it.coordinates, *_make_names(3)) for i, it in enumerate(all_pts[:-1])]
        repo = MockedLayer2Repository(all_in_repo)

        use_case = CrossIdentifyUseCase(repo)

        obj_names = [all_in_repo[0].names[0], all_in_repo[1].names[0]]
        res = use_case.invoke(
            CrossIdentificationParam(obj_names, obj_names[0], None),
            SimpleSimultaneousDataProvider([CrossIdentificationParam(*_make_names(1), None) for _ in range(20)]),
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsInstance(res.fail, CrossIdentificationNamesDuplicateException)
        self.assertEqual(res.fail.names, obj_names)

    def test_identify_by_name_and_coordinates(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec)
        target_name = uuid4().hex
        target_id = 256

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [
            CrossIdentificationParam(*_make_names(1), it.coordinates) for it in all_pts if it not in inside_proc
        ] + [CrossIdentificationParam([target_name], target_name, target)]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, *_make_names(3)) for i, it in enumerate(outside)]
            + [_make_l2(target_id, target, [target_name, uuid4().hex, uuid4().hex], target_name)]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam([target_name], target_name, center),
            data_provider,
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsNone(res.fail, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    def test_identify_by_name_and_coordinates_new_object(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [
            CrossIdentificationParam(*_make_names(1), it.coordinates) for it in all_pts if it not in inside_proc
        ]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, *_make_names(1)) for i, it in enumerate(outside)])

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam(*_make_names(1), center), data_provider, CrossIdentificationUserParam(None, None)
        )

        self.assertIsNone(res.fail, "Cross identification must pass")
        self.assertEqual(res.result, None)

    def test_name_coord_collision(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec)
        target1_name = uuid4().hex
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + INNER_RADIUS * 30)
        target2_name = uuid4().hex
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, *_make_names(1)) for i, it in enumerate(outside)]
            + [
                _make_l2(target1_id, target1, [target1_name], target1_name),
                _make_l2(target2_id, target2, [target2_name], target2_name),
            ]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam([target2_name], target2_name, center),
            data_provider,
            CrossIdentificationUserParam(None, None),
        )
        self.assertIsInstance(
            res.fail,
            CrossIdentificationNameCoordCollisionException,
            "Cross identification must fail with 'CrossIdentificationNameCoordCollisionException'",
        )

    def test_name_coord_both_fail(self):
        """
        Case, where names collide by CrossIdentificationNamesDuplicateException,
        and coordinates collide by CrossIdentificationCoordCollisionException
        """
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec)
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + INNER_RADIUS / 2)
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [
            CrossIdentificationParam(*_make_names(2), it.coordinates) for it in all_pts if it not in inside_proc
        ] + [CrossIdentificationParam(*_make_names(2), center)]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        all_in_repo = [_make_l2(i, it.coordinates, *_make_names(2)) for i, it in enumerate(outside)] + [
            _make_l2(target1_id, target1, *_make_names(2)),
            _make_l2(target2_id, target2, *_make_names(2)),
        ]
        repo = MockedLayer2Repository(all_in_repo)

        use_case = CrossIdentifyUseCase(repo)

        obj_names = [all_in_repo[-1].names[0], all_in_repo[-2].names[1]]
        res = use_case.invoke(
            CrossIdentificationParam(obj_names, obj_names[0], center),
            data_provider,
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsInstance(
            res.fail,
            CrossIdentificationNameCoordFailException,
            "Cross identification must fail with 'CrossIdentificationNameCoordFailException'",
        )
        self.assertIsInstance(res.fail.name_collision, CrossIdentificationNamesDuplicateException)
        self.assertEqual(res.fail.name_collision.names, obj_names)
        self.assertIsInstance(res.fail.coord_collision, CrossIdentificationCoordCollisionException)
        self.assertEqual(res.fail.coord_collision.collisions, all_in_repo[-2:])

    def test_name_coord_fail_name(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [
            CrossIdentificationParam(*_make_names(1), it.coordinates) for it in all_pts if it not in inside_proc
        ]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        all_in_repo = [_make_l2(i, it.coordinates, *_make_names(1)) for i, it in enumerate(outside)]
        repo = MockedLayer2Repository(all_in_repo)

        use_case = CrossIdentifyUseCase(repo)

        obj_names = [all_in_repo[0].names[0], all_in_repo[1].names[0]]
        res = use_case.invoke(
            CrossIdentificationParam(obj_names, obj_names[0], center),
            data_provider,
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsInstance(
            res.fail,
            CrossIdentificationNameCoordNameFailException,
            "Cross identification must fail with 'CrossIdentificationNameCoordNameFailException'",
        )
        self.assertEqual(res.fail.coord_hit, None)
        self.assertIsInstance(res.fail.name_collision, CrossIdentificationNamesDuplicateException)
        self.assertEqual(res.fail.name_collision.names, obj_names)

    def test_name_coord_name_fail_coord_success(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target = ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec)
        target_id = 256

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [
            CrossIdentificationParam(*_make_names(1), it.coordinates) for it in all_pts if it not in inside_proc
        ] + [CrossIdentificationParam(*_make_names(2), target)]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, *_make_names(3)) for i, it in enumerate(outside)]
            + [_make_l2(target_id, target, *_make_names(3))]
        )

        use_case = CrossIdentifyUseCase(repo)

        obj_names, obj_name = outside_proc[-1].names, outside_proc[-1].primary_name
        res = use_case.invoke(
            CrossIdentificationParam(obj_names, obj_name, center),
            data_provider,
            CrossIdentificationUserParam(None, None),
        )

        self.assertIsNone(res.fail, "Cross identification must pass")
        self.assertEqual(target_id, res.result.pgc)

    def test_name_coord_fail_coord(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec)
        target1_name = uuid4().hex
        target1_id = 256
        target2 = ICRS(ra=center.ra, dec=center.dec + INNER_RADIUS / 2)
        target2_name = uuid4().hex
        target2_id = 666

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [
            CrossIdentificationParam(*_make_names(1), it.coordinates) for it in all_pts if it not in inside_proc
        ] + [CrossIdentificationParam([target2_name], target2_name, target2)]

        data_provider = SimpleSimultaneousDataProvider(outside_proc)

        repo = MockedLayer2Repository(
            [_make_l2(i, it.coordinates, *_make_names(3)) for i, it in enumerate(outside)]
            + [
                _make_l2(target1_id, target1, [target1_name], target1_name),
                _make_l2(target2_id, target2, [target2_name], target2_name),
            ]
        )

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam([target2_name], target2_name, center),
            data_provider,
            CrossIdentificationUserParam(None, None),
        )
        if isinstance(res.fail, CrossIdentificationNameCoordCoordException):
            self.assertEqual(res.fail.name_hit.pgc, target2_id)
        else:
            self.fail("Cross identification must fail with 'CrossIdentificationNameCoordCoordException'")

    def test_simultaneous_name_fail(self):
        target1 = CrossIdentificationParam(*_make_names(2), None)
        target2 = CrossIdentificationParam(*_make_names(2), None)

        all_pts, inside = make_points(n_points=100, center=ICRS(ra=20 * u.deg, dec=40 * u.deg), r=10 * u.deg)

        data_provider = SimpleSimultaneousDataProvider(all_pts + [target1, target2])

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, *_make_names(3)) for i, it in enumerate(all_pts)])

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam(target1.names + target2.names, target2.primary_name, None),
            data_provider,
            CrossIdentificationUserParam(None, None),
        )
        self.assertIsInstance(res.fail, CrossIdentificationDuplicateException)
        self.assertTrue(target1 in res.fail.collisions)
        self.assertTrue(target2 in res.fail.collisions)

    def test_simultaneous_coord_fail(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)
        target1 = CrossIdentificationParam(None, None, ICRS(ra=center.ra + INNER_RADIUS / 2, dec=center.dec))
        target2 = CrossIdentificationParam(None, None, ICRS(ra=center.ra, dec=center.dec + INNER_RADIUS / 2))

        all_pts, inside = make_points(n_points=100, center=center, r=r)
        outside = [it for it in all_pts if it not in inside]

        all_pts_proc, inside_proc = make_points(n_points=20, center=center, r=r)
        outside_proc = [it for it in all_pts if it not in inside_proc]

        data_provider = SimpleSimultaneousDataProvider(outside_proc + [target1, target2])

        repo = MockedLayer2Repository([_make_l2(i, it.coordinates, None, None) for i, it in enumerate(outside)])

        use_case = CrossIdentifyUseCase(repo)

        res = use_case.invoke(
            CrossIdentificationParam(None, None, center), data_provider, CrossIdentificationUserParam(None, None)
        )
        self.assertIsInstance(res.fail, CrossIdentificationDuplicateException)
        self.assertIsInstance(res.fail.db_cross_id_result, CrossIdentifyResult)
        self.assertTrue(target1 in res.fail.collisions)
        self.assertTrue(target2 in res.fail.collisions)
