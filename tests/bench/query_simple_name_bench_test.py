import logging
import time
import unittest

import structlog

from tests import lib
from tests.bench import layer2_seed

PARAMS = {"name": layer2_seed.CLUSTER_NAME, "page": 0, "page_size": 25}
MAX_MEDIAN_SECONDS = 1.0


class QuerySimpleNameBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.storage = cls.pg_storage.get_storage()

        print(f"\nSeeding {layer2_seed.N_OBJECTS} layer2 objects...")
        seed_started = time.perf_counter()
        layer2_seed.seed_layer2(cls.storage, layer2_seed.N_OBJECTS)
        print(f"Seed completed in {time.perf_counter() - seed_started:.2f}s")

        cls.client, cls.url = layer2_seed.build_client(cls.storage)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pg_storage.clear()

    def test_name_query_latency(self) -> None:
        response = self.client.get(self.url, params=PARAMS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["objects"]), PARAMS["page_size"])

        median = layer2_seed.measure(
            lambda: self.client.get(self.url, params=PARAMS).status_code,
            "query/simple name",
        )

        self.assertLess(median, MAX_MEDIAN_SECONDS)
