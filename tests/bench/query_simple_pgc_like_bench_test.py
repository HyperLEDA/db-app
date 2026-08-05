import unittest

from tests.bench import layer2_seed

PARAMS = {"pgc_like": 12, "page": 0, "page_size": 25}
MAX_MEDIAN_SECONDS = 1.0


class QuerySimplePgcLikeBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage, cls.client, cls.url = layer2_seed.setup_query_simple_bench()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.pg_storage.clear()

    def test_pgc_like_query_latency(self) -> None:
        response = self.client.get(self.url, params=PARAMS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["objects"]), PARAMS["page_size"])

        median = layer2_seed.measure(
            lambda: self.client.get(self.url, params=PARAMS).status_code,
            "query/simple pgc_like",
        )

        self.assertLess(median, MAX_MEDIAN_SECONDS)
