import logging
import os
import time
import unittest

import structlog

from app import tasks
from app.data import model, repositories
from app.tasks import layer2_import_icrs
from tests import lib

N_OBJECTS = int(os.environ.get("BENCH_ICRS_N_OBJECTS", "50000"))
MEASUREMENTS_PER_OBJECT = int(os.environ.get("BENCH_ICRS_MEASUREMENTS_PER_OBJECT", "2"))


class Layer2ImportIcrsBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.storage = cls.pg_storage.get_storage()
        logger = structlog.get_logger()
        cls.common_repo = repositories.CommonRepository(cls.storage, logger)
        cls.layer0_repo = repositories.Layer0Repository(cls.storage, logger)
        cls.task = layer2_import_icrs.Layer2ImportICRSTask(logger, silent=True)
        cls.task.prepare(tasks.Config(storage=cls.pg_storage.config))

    def tearDown(self) -> None:
        self.pg_storage.clear()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.task.cleanup()

    def _seed_layer1_icrs(self, n_objects: int, measurements_per_object: int) -> None:
        bib_id = self.common_repo.create_bibliography("bench_icrs", 2000, ["bench"], "bench icrs import")
        table_resp = self.layer0_repo.create_table(model.Layer0TableMeta("bench_icrs_import", [], bib_id))
        table_id = table_resp.table_id
        n_records = n_objects * measurements_per_object

        self.storage.exec(
            "INSERT INTO common.pgc (id) SELECT generate_series(1, %s) ON CONFLICT (id) DO NOTHING",
            params=[n_objects],
        )
        self.storage.exec(
            """
            INSERT INTO layer0.records (id, table_id, pgc)
            SELECT
                'bench_icrs_' || i::text,
                %s,
                ((i - 1) / %s) + 1
            FROM generate_series(1, %s) AS i
            """,
            params=[table_id, measurements_per_object, n_records],
        )
        self.storage.exec(
            """
            UPDATE common.pgc
            SET modification_time = NOW()
            WHERE id BETWEEN 1 AND %s
            """,
            params=[n_objects],
        )
        self.storage.exec(
            """
            INSERT INTO icrs.data (record_id, ra, e_ra, dec, e_dec)
            SELECT
                'bench_icrs_' || i::text,
                (i %% 360)::double precision,
                0.1::real,
                (((i %% 180) - 90))::double precision,
                0.1::real
            FROM generate_series(1, %s) AS i
            """,
            params=[n_records],
        )

    def test_layer2_import_icrs_throughput(self) -> None:
        print(
            f"\nSeeding {N_OBJECTS} PGCs with {MEASUREMENTS_PER_OBJECT} ICRS measurements each "
            f"({N_OBJECTS * MEASUREMENTS_PER_OBJECT} layer1 rows)..."
        )
        seed_started = time.perf_counter()
        self._seed_layer1_icrs(N_OBJECTS, MEASUREMENTS_PER_OBJECT)
        seed_elapsed = time.perf_counter() - seed_started
        print(f"Seed completed in {seed_elapsed:.2f}s")

        started = time.perf_counter()
        self.task.run()
        elapsed = time.perf_counter() - started

        layer2_count = self.storage.query_one("SELECT count(*) AS n FROM layer2.icrs")["n"]
        self.assertEqual(int(layer2_count), N_OBJECTS)

        rate = N_OBJECTS / elapsed if elapsed > 0 else float("inf")
        print(
            f"Layer2 ICRS import: {elapsed:.2f}s for {N_OBJECTS} objects "
            f"({rate:.0f} objects/s, {MEASUREMENTS_PER_OBJECT} measurements/object)"
        )
