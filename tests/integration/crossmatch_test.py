import unittest

import structlog

from app.data import repositories
from tests import lib


class CrossmatchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()
        cls.layer2_repo = repositories.Layer2Repository(cls.pg_storage.get_storage(), structlog.get_logger())

    def tearDown(self):
        self.pg_storage.clear()

    def test_no_existing_objects(self):
        pass

    def test_one_intersection(self):
        pass

    def test_several_intersections(self):
        pass

    def test_batch(self):
        pass
