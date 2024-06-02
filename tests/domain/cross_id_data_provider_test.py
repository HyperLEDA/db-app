import unittest
from math import pi
import random
import tracemalloc
import timeit
from typing import Callable

from astropy.coordinates import ICRS, angular_separation, Angle
import astropy.units as u

from app.data.repositories.tmp_data_repository_impl import TmpDataRepositoryImpl
from app.domain.cross_id_simultaneous_data_provider import SimpleSimultaneousDataProvider, \
    KDTreeSimultaneousDataProvider, PostgreSimultaneousDataProvider
from app.domain.model.params import CrossIdentificationParam
from app.lib import testing, exceptions


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

        all_pts, inside = self._make_points(n_points=5000, center=center, r=r)
        inside.sort(key=lambda it: it.coordinates.ra)

        data_provider = SimpleSimultaneousDataProvider(all_pts)
        got_inside = data_provider.data_inside(center, r)
        got_inside.sort(key=lambda it: it.coordinates.ra)

        kdtree_provider = KDTreeSimultaneousDataProvider(all_pts)
        kd_inside = kdtree_provider.data_inside(center, r)
        kd_inside.sort(key=lambda it: it.coordinates.ra)

        pg_provider = PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository)
        pg_inside = pg_provider.data_inside(center, r)
        pg_inside.sort(key=lambda it: it.coordinates.ra)

        # Check PostgreSimultaneousDataProvider removed temporary table
        pg_provider.clear()
        self.assertRaises(
            exceptions.APIException,
            lambda: self.storage.get_storage().query(f"SELECT * FROM {pg_provider._table_name}")
        )

        self.assertListEqual(inside, got_inside)
        self.assertListEqual(inside, kd_inside)
        self.assertListEqual(inside, pg_inside)

    @unittest.skip("Only for benchmarking")
    def test_simple_provider(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        def call_for_n_points(n_points: int):
            all_pts, inside = self._make_points(n_points=n_points, center=center, r=r)

            t_init, b_init = self._print_benchmark(lambda: SimpleSimultaneousDataProvider(all_pts))

            data_provider = SimpleSimultaneousDataProvider(all_pts)

            def call():
                got_inside = data_provider.data_inside(center, r)

            t_call, b_call = self._print_benchmark(call)
            print()
            print(f"{n_points} | simple | {t_init} s | {b_init} B | {t_call} s | {b_call} B")

        for n in [1000, 5000, 10000, 20000, 50000, 100000]:
            call_for_n_points(n)

    @unittest.skip("Only for benchmarking")
    def test_kd_provider(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        def call_for_n_points(n_points: int):
            all_pts, inside = self._make_points(n_points=n_points, center=center, r=r)

            t_init, b_init = self._print_benchmark(lambda: KDTreeSimultaneousDataProvider(all_pts))

            data_provider = KDTreeSimultaneousDataProvider(all_pts)

            def call():
                got_inside = data_provider.data_inside(center, r)

            t_call, b_call = self._print_benchmark(call)
            print()
            print(f"{n_points} | KDTree | {t_init} s | {b_init} B | {t_call} s | {b_call} B")

        for n in [1000, 5000, 10000, 20000, 50000, 100000]:
            call_for_n_points(n)

    @unittest.skip("Only for benchmarking")
    def test_pg_provider(self):
        r = 10 * u.deg
        center = ICRS(ra=20 * u.deg, dec=40 * u.deg)

        def call_for_n_points(n_points: int):
            all_pts, inside = self._make_points(n_points=n_points, center=center, r=r)

            t_init, b_init = self._print_benchmark(lambda: PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository), n_calls=2)

            data_provider = PostgreSimultaneousDataProvider(all_pts, self._tmp_data_repository)

            def call():
                got_inside = data_provider.data_inside(center, r)

            t_call, b_call = self._print_benchmark(call)
            print()
            print(f"{n_points} | PG | {t_init} s | {b_init} B | {t_call} s | {b_call} B")

        for n in [1000, 5000, 10000, 20000, 50000, 100000]:
            call_for_n_points(n)

    @staticmethod
    def _print_benchmark(call: Callable, n_calls: int = 10) -> tuple[float, int]:
        tracemalloc.start()

        t_sec = timeit.timeit(call, number=n_calls) / n_calls
        mem = tracemalloc.take_snapshot()

        tracemalloc.stop()

        n_bytes = sum(it.size for it in mem.traces)

        return t_sec, n_bytes

    def _make_points(
            self,
            n_points: int,
            center: ICRS,
            r: Angle,
    ) -> tuple[list[CrossIdentificationParam], list[CrossIdentificationParam]]:
        ra = [2 * pi * random.random() for _ in range(0, n_points)]
        dec = [pi * random.random() - pi / 2 for _ in range(0, n_points)]
        all_pts = [
            CrossIdentificationParam(None, ICRS(ra=it[0] * u.rad, dec=it[1] * u.rad))
            for it in zip(ra, dec)
        ]

        inside = [
            it for it in all_pts
            if angular_separation(it.coordinates.ra, it.coordinates.dec, center.ra, center.dec) <= r
        ]

        return all_pts, inside
