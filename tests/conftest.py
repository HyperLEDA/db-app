from collections.abc import Generator

import pytest

from app.lib.storage import enums
from tests.lib.postgres import PostgresTestStorage


@pytest.fixture(scope="session")
def pg_storage() -> PostgresTestStorage:
    return PostgresTestStorage.get(enums.PG_ENUM_REGISTRY)


@pytest.fixture
def cleared_pg_storage(pg_storage: PostgresTestStorage) -> Generator[PostgresTestStorage]:
    yield pg_storage
    pg_storage.clear()
