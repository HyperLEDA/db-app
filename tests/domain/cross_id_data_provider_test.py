import timeit
import tracemalloc
import unittest
from typing import Callable
from uuid import uuid4

import astropy.units as u
from astropy.coordinates import ICRS

from app.data.repositories.tmp_data_repository_impl import TmpDataRepositoryImpl
from app.domain.cross_id_simultaneous_data_provider import (
    PostgreSimultaneousDataProvider,
    SimpleSimultaneousDataProvider,
)
from app.domain.model.params import CrossIdentificationParam
from app.lib import exceptions, testing
from tests.domain.util import make_points


class CrossIdDataProviderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.storage = testing.get_test_postgres_storage()

        cls._tmp_data_repository: TmpDataRepositoryImpl = TmpDataRepositoryImpl(cls.storage.get_storage())

    def tearDown(self):
        self.storage.clear()

    def test_data_inside(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        all_pts, inside = make_points(n_points=5000, center=center, r=r)
        inside.sort(key=lambda it: it.coordinates.ra)

        data_provider = SimpleSimultaneousDataProvider(all_pts)
        got_inside = data_provider.data_inside(center, r)
        got_inside.sort(key=lambda it: it.coordinates.ra)

        pg_provider = PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository)
        pg_inside = pg_provider.data_inside(center, r)
        pg_inside.sort(key=lambda it: it.coordinates.ra)

        # Check PostgreSimultaneousDataProvider removed temporary table
        pg_provider.clear()
        self.assertRaises(
            exceptions.APIException,
            lambda: self.storage.get_storage().query(f"SELECT * FROM {pg_provider.table_name}"),
        )

        self.assertListEqual(inside, got_inside)
        self.assertListEqual(inside, pg_inside)

    def test_data_by_name(self):
        all_pts = [
            CrossIdentificationParam(lst, lst[0], None) for lst in [[uuid4().hex, uuid4().hex] for _ in range(100)]
        ]
        lst = [uuid4().hex, uuid4().hex, uuid4().hex, uuid4().hex]
        target = CrossIdentificationParam(lst, lst[0], None)
        all_pts = all_pts + [target]

        data_provider = SimpleSimultaneousDataProvider(all_pts)
        provider_res = data_provider.by_name(target.names)

        pg_provider = PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository)
        pg_res = pg_provider.by_name(target.names[:2])

        self.assertEqual(len(provider_res), 1)
        self.assertEqual(provider_res[0], target)

        self.assertEqual(len(pg_res), 1)
        self.assertEqual(pg_res[0], target)

    @unittest.skip("Only for benchmarking")
    def test_simple_provider(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        def call_for_n_points(n_points: int):
            all_pts, inside = make_points(n_points=n_points, center=center, r=r)

            t_init, b_init = self._print_benchmark(lambda: SimpleSimultaneousDataProvider(all_pts))

            data_provider = SimpleSimultaneousDataProvider(all_pts)

            def call():
                data_provider.data_inside(center, r)

            t_call, b_call = self._print_benchmark(call)
            print()
            print(f"{n_points} | simple | {t_init} s | {b_init} B | {t_call} s | {b_call} B")

        for n in [1000, 5000, 10000, 20000, 50000, 100000]:
            call_for_n_points(n)

    @unittest.skip("Only for benchmarking")
    def test_pg_provider(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        def call_for_n_points(n_points: int):
            all_pts, inside = make_points(n_points=n_points, center=center, r=r)

            t_init, b_init = self._print_benchmark(
                lambda: PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository), n_calls=2
            )

            data_provider = PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository)

            def call():
                data_provider.data_inside(center, r)

            t_call, b_call = self._print_benchmark(call)
            print()
            print(f"{n_points} | PG | {t_init} s | {b_init} B | {t_call} s | {b_call} B")

        for n in [1000, 5000, 10000, 20000, 50000, 100000]:
            call_for_n_points(n)

    def test_65_fail(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        n_points = 100000

        all_pts, inside = make_points(n_points=n_points, center=center, r=r)
        data_provider = PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository)

    @staticmethod
    def _print_benchmark(call: Callable, n_calls: int = 10) -> tuple[float, int]:
        tracemalloc.start()

        t_sec = timeit.timeit(call, number=n_calls) / n_calls
        mem = tracemalloc.take_snapshot()

        tracemalloc.stop()

        n_bytes = sum(it.size for it in mem.traces)

        return t_sec, n_bytes
