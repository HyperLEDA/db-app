from collections.abc import Generator

import pytest

from app.lib.storage import enums
from tests.lib.postgres import TestPostgresStorage


@pytest.fixture(scope="session")
def pg_storage() -> TestPostgresStorage:
    return TestPostgresStorage.get(enums.PG_ENUM_REGISTRY)


@pytest.fixture
def cleared_pg_storage(pg_storage: TestPostgresStorage) -> Generator[TestPostgresStorage]:
    yield pg_storage
    pg_storage.clear()
