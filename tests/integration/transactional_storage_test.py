import unittest

from app.lib.storage.postgres import transactional
from tests import lib


class TransactionalRepositoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pg_storage = lib.TestPostgresStorage.get()

    def test_several_queries(self):
        repo = transactional.TransactionalPGRepository(self.pg_storage.get_storage())
        with repo.with_tx():
            self.pg_storage.get_storage().exec("CREATE TABLE test_table1 (id INTEGER)")
            self.pg_storage.get_storage().exec("INSERT INTO test_table1 VALUES (42)")
            result = self.pg_storage.get_storage().query_one("SELECT id FROM test_table1 LIMIT 1")

        self.assertEqual(result["id"], 42)

    def test_nested_transactions(self):
        repo = transactional.TransactionalPGRepository(self.pg_storage.get_storage())
        with repo.with_tx():
            self.pg_storage.get_storage().exec("CREATE TABLE test_table2 (id INTEGER)")
            with repo.with_tx():
                self.pg_storage.get_storage().exec("INSERT INTO test_table2 VALUES (42)")
                result = self.pg_storage.get_storage().query_one("SELECT id FROM test_table2 LIMIT 1")

        self.assertEqual(result["id"], 42)

    def test_rollback_queries(self):
        repo = transactional.TransactionalPGRepository(self.pg_storage.get_storage())
        try:
            with repo.with_tx():
                self.pg_storage.get_storage().exec("CREATE TABLE test_table3 (id INTEGER)")
                self.pg_storage.get_storage().exec("INSERT INTO test_table3 VALUES (42)")
                self.pg_storage.get_storage().exec("INSERT INTO test_table3 VALUES ('totally not integer')")
        except Exception:
            pass

        with self.assertRaises(Exception):
            self.pg_storage.get_storage().query_one("SELECT id FROM test_table3 LIMIT 1")

    def test_rollback_expressions(self):
        repo = transactional.TransactionalPGRepository(self.pg_storage.get_storage())
        try:
            with repo.with_tx():
                self.pg_storage.get_storage().exec("CREATE TABLE test_table4 (id INTEGER)")
                self.pg_storage.get_storage().exec("INSERT INTO test_table4 VALUES (42)")

                raise Exception("Some exception")

        except Exception:
            pass

        with self.assertRaises(Exception):
            self.pg_storage.get_storage().query_one("SELECT id FROM test_table4 LIMIT 1")
