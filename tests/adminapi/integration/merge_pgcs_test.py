import datetime
import uuid

import pydantic
import pytest
import structlog

from app.adminapi import model, repository
from app.adminapi.domain import pgc
from app.lib.storage import postgres
from app.lib.web import errors
from app.specs import adminapi
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def repo(pg_storage: PostgresTestStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


@pytest.fixture(scope="module")
def manager(repo: repository.Repository) -> pgc.PgcManager:
    return pgc.PgcManager(repo)


def _create_table(repo: repository.Repository, table_name: str) -> None:
    bib_id = repo.create_bibliography("123456", 2000, ["test"], "test")
    repo.create_table(
        model.Layer0TableMeta(
            postgres.TableInfo(schema=repository.RAWDATA_SCHEMA, name=table_name),
            bib_id,
        )
    )


def _register_with_pgcs(
    repo: repository.Repository,
    table_name: str,
    record_pgcs: dict[str, int],
) -> None:
    _create_table(repo, table_name)
    record_ids = list(record_pgcs.keys())
    repo.register_records(table_name, record_ids)
    repo.register_pgcs(list(set(record_pgcs.values())))
    repo.upsert_pgc(dict(record_pgcs))


def _pgc_for(pg_storage: PostgresTestStorage, record_id: str) -> int | None:
    row = pg_storage.storage.query_one(
        "SELECT pgc FROM layer0.records WHERE id = %s",
        params=[record_id],
    )
    return row["pgc"]


def _modification_time(pg_storage: PostgresTestStorage, pgc_id: int) -> datetime.datetime:
    row = pg_storage.storage.query_one(
        "SELECT modification_time FROM common.pgc WHERE id = %s",
        params=[pgc_id],
    )
    return row["modification_time"]


def test_merge_multiple_sources_onto_target(
    repo: repository.Repository,
    manager: pgc.PgcManager,
    pg_storage: PostgresTestStorage,
) -> None:
    target_pgc = 100
    source_a = 200
    source_b = 300
    target_id = str(uuid.uuid4())
    source_a_id = str(uuid.uuid4())
    source_b_id = str(uuid.uuid4())
    _register_with_pgcs(
        repo,
        "merge_multi",
        {
            target_id: target_pgc,
            source_a_id: source_a,
            source_b_id: source_b,
        },
    )

    old_dt = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    pg_storage.storage.exec(
        "UPDATE common.pgc SET modification_time = %s WHERE id = ANY(%s)",
        params=[old_dt, [target_pgc, source_a, source_b]],
    )

    response = manager.merge_pgcs(
        adminapi.MergePgcsRequest(target_pgc=target_pgc, source_pgcs=[source_a, source_b]),
    )

    assert response.target_pgc == target_pgc
    assert response.merged_pgcs == [source_a, source_b]
    assert response.reassigned_records == 2
    assert _pgc_for(pg_storage, target_id) == target_pgc
    assert _pgc_for(pg_storage, source_a_id) == target_pgc
    assert _pgc_for(pg_storage, source_b_id) == target_pgc
    assert _modification_time(pg_storage, target_pgc).replace(tzinfo=datetime.UTC) > old_dt
    assert _modification_time(pg_storage, source_a).replace(tzinfo=datetime.UTC) > old_dt
    assert _modification_time(pg_storage, source_b).replace(tzinfo=datetime.UTC) > old_dt


def test_reject_target_in_sources() -> None:
    with pytest.raises(pydantic.ValidationError):
        adminapi.MergePgcsRequest(target_pgc=100, source_pgcs=[100, 200])


def test_reject_duplicate_sources() -> None:
    with pytest.raises(pydantic.ValidationError):
        adminapi.MergePgcsRequest(target_pgc=100, source_pgcs=[200, 200])


def test_reject_missing_target(repo: repository.Repository, manager: pgc.PgcManager) -> None:
    source_pgc = 9_000_001
    missing_target = 9_000_002
    repo.register_pgcs([source_pgc])

    with pytest.raises(errors.NotFoundError):
        manager.merge_pgcs(
            adminapi.MergePgcsRequest(target_pgc=missing_target, source_pgcs=[source_pgc]),
        )


def test_reject_missing_source(repo: repository.Repository, manager: pgc.PgcManager) -> None:
    target_pgc = 9_000_003
    missing_source = 9_000_004
    repo.register_pgcs([target_pgc])

    with pytest.raises(errors.NotFoundError):
        manager.merge_pgcs(
            adminapi.MergePgcsRequest(target_pgc=target_pgc, source_pgcs=[missing_source]),
        )
