import pytest

from app.lib.storage.postgres import transactional
from tests.lib.postgres import PostgresTestStorage


def test_several_queries(pg_storage: PostgresTestStorage) -> None:
    repo = transactional.TransactionalPGRepository(pg_storage.get_storage())
    with repo.with_tx():
        pg_storage.get_storage().exec("CREATE TABLE test_table1 (id INTEGER)")
        pg_storage.get_storage().exec("INSERT INTO test_table1 VALUES (42)")
        result = pg_storage.get_storage().query_one("SELECT id FROM test_table1 LIMIT 1")

    assert result["id"] == 42


def test_multiple_statements_in_transaction(pg_storage: PostgresTestStorage) -> None:
    repo = transactional.TransactionalPGRepository(pg_storage.get_storage())
    with repo.with_tx():
        pg_storage.get_storage().exec("CREATE TABLE test_table2 (id INTEGER)")
        pg_storage.get_storage().exec("INSERT INTO test_table2 VALUES (42)")
        result = pg_storage.get_storage().query_one("SELECT id FROM test_table2 LIMIT 1")

    assert result["id"] == 42


def test_rollback_queries(pg_storage: PostgresTestStorage) -> None:
    repo = transactional.TransactionalPGRepository(pg_storage.get_storage())
    try:
        with repo.with_tx():
            pg_storage.get_storage().exec("CREATE TABLE test_table3 (id INTEGER)")
            pg_storage.get_storage().exec("INSERT INTO test_table3 VALUES (42)")
            pg_storage.get_storage().exec("INSERT INTO test_table3 VALUES ('totally not integer')")
    except Exception:
        pass

    with pytest.raises(Exception):
        pg_storage.get_storage().query_one("SELECT id FROM test_table3 LIMIT 1")


def test_rollback_expressions(pg_storage: PostgresTestStorage) -> None:
    repo = transactional.TransactionalPGRepository(pg_storage.get_storage())
    try:
        with repo.with_tx():
            pg_storage.get_storage().exec("CREATE TABLE test_table4 (id INTEGER)")
            pg_storage.get_storage().exec("INSERT INTO test_table4 VALUES (42)")

            raise Exception("Some exception")

    except Exception:
        pass

    with pytest.raises(Exception):
        pg_storage.get_storage().query_one("SELECT id FROM test_table4 LIMIT 1")
