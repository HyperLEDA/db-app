import datetime
import uuid

import pytest
import structlog

from app.adminapi import model, repository
from app.adminapi.domain import crossmatch
from app.lib.storage import enums, postgres
from app.lib.web import errors
from app.specs import adminapi
from tests.lib.postgres import TestPostgresStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


@pytest.fixture(scope="module")
def repo(pg_storage: TestPostgresStorage) -> repository.Repository:
    return repository.Repository(pg_storage.get_storage(), structlog.get_logger())


@pytest.fixture(scope="module")
def manager(repo: repository.Repository) -> crossmatch.CrossmatchManager:
    return crossmatch.CrossmatchManager(repo)


def _create_table(repo: repository.Repository, table_name: str) -> None:
    bib_id = repo.create_bibliography("123456", 2000, ["test"], "test")
    repo.create_table(
        model.Layer0TableMeta(
            postgres.TableInfo(schema=repository.RAWDATA_SCHEMA, name=table_name),
            bib_id,
        )
    )


def _register(repo: repository.Repository, table_name: str, record_ids: list[str]) -> None:
    _create_table(repo, table_name)
    repo.register_records(table_name, record_ids)


def _set_crossmatch(
    repo: repository.Repository,
    rows: list[tuple[str, enums.RecordTriageStatus, list[int]]],
) -> None:
    repo.set_crossmatch_results(rows)


def _pgc_for(pg_storage: TestPostgresStorage, record_id: str) -> int | None:
    row = pg_storage.storage.query_one(
        "SELECT pgc FROM layer0.records WHERE id = %s",
        params=[record_id],
    )
    return row["pgc"]


def test_submit_new_and_existing_records(
    repo: repository.Repository,
    manager: crossmatch.CrossmatchManager,
    pg_storage: TestPostgresStorage,
) -> None:
    table_name = "submit_happy"
    new_id = str(uuid.uuid4())
    existing_id = str(uuid.uuid4())
    existing_pgc = 4242
    _register(repo, table_name, [new_id, existing_id])
    repo.register_pgcs([existing_pgc])
    _set_crossmatch(
        repo,
        [
            (new_id, enums.RecordTriageStatus.RESOLVED, []),
            (existing_id, enums.RecordTriageStatus.RESOLVED, [existing_pgc]),
        ],
    )

    old_dt = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
    pg_storage.storage.exec(
        "UPDATE common.pgc SET modification_time = %s WHERE id = %s",
        params=[old_dt, existing_pgc],
    )

    manager.assign_record_pgcs(adminapi.AssignRecordPgcsRequest(record_ids=[new_id, existing_id]))

    new_pgc = _pgc_for(pg_storage, new_id)
    assert new_pgc is not None
    assert _pgc_for(pg_storage, existing_id) == existing_pgc
    assert new_pgc != existing_pgc
    existing_mt = pg_storage.storage.query_one(
        "SELECT modification_time FROM common.pgc WHERE id = %s",
        params=[existing_pgc],
    )["modification_time"]
    assert existing_mt.replace(tzinfo=datetime.UTC) > old_dt
    new_mt = pg_storage.storage.query_one(
        "SELECT modification_time FROM common.pgc WHERE id = %s",
        params=[new_pgc],
    )["modification_time"]
    assert new_mt.replace(tzinfo=datetime.UTC) > old_dt


def test_reject_pending_records(
    repo: repository.Repository,
    manager: crossmatch.CrossmatchManager,
    pg_storage: TestPostgresStorage,
) -> None:
    table_name = "submit_pending"
    pending_id = str(uuid.uuid4())
    resolved_id = str(uuid.uuid4())
    _register(repo, table_name, [pending_id, resolved_id])
    _set_crossmatch(
        repo,
        [
            (pending_id, enums.RecordTriageStatus.PENDING, []),
            (resolved_id, enums.RecordTriageStatus.RESOLVED, []),
        ],
    )

    with pytest.raises(errors.ConflictError) as exc_info:
        manager.assign_record_pgcs(
            adminapi.AssignRecordPgcsRequest(record_ids=[pending_id, resolved_id]),
        )

    assert exc_info.value.count == 1
    assert pending_id in (exc_info.value.sample_record_ids or [])
    assert _pgc_for(pg_storage, pending_id) is None
    assert _pgc_for(pg_storage, resolved_id) is None


def test_reject_missing_crossmatch_row(
    repo: repository.Repository,
    manager: crossmatch.CrossmatchManager,
    pg_storage: TestPostgresStorage,
) -> None:
    table_name = "submit_missing"
    missing_id = str(uuid.uuid4())
    _register(repo, table_name, [missing_id])

    with pytest.raises(errors.ConflictError) as exc_info:
        manager.assign_record_pgcs(adminapi.AssignRecordPgcsRequest(record_ids=[missing_id]))

    assert exc_info.value.count == 1
    assert _pgc_for(pg_storage, missing_id) is None


def test_reject_collided_metadata(
    repo: repository.Repository,
    manager: crossmatch.CrossmatchManager,
    pg_storage: TestPostgresStorage,
) -> None:
    table_name = "submit_collided"
    collided_id = str(uuid.uuid4())
    _register(repo, table_name, [collided_id])
    repo.register_pgcs([10, 11])
    _set_crossmatch(
        repo,
        [(collided_id, enums.RecordTriageStatus.RESOLVED, [10, 11])],
    )

    with pytest.raises(errors.ConflictError):
        manager.assign_record_pgcs(adminapi.AssignRecordPgcsRequest(record_ids=[collided_id]))

    assert _pgc_for(pg_storage, collided_id) is None


def test_idempotent_retry(
    repo: repository.Repository,
    manager: crossmatch.CrossmatchManager,
    pg_storage: TestPostgresStorage,
) -> None:
    table_name = "submit_retry"
    record_id = str(uuid.uuid4())
    _register(repo, table_name, [record_id])
    _set_crossmatch(repo, [(record_id, enums.RecordTriageStatus.RESOLVED, [])])

    request = adminapi.AssignRecordPgcsRequest(record_ids=[record_id])
    manager.assign_record_pgcs(request)
    first_pgc = _pgc_for(pg_storage, record_id)
    assert first_pgc is not None

    pgc_count_before = pg_storage.storage.query_one("SELECT COUNT(*)::int AS cnt FROM common.pgc")["cnt"]
    manager.assign_record_pgcs(request)
    pgc_count_after = pg_storage.storage.query_one("SELECT COUNT(*)::int AS cnt FROM common.pgc")["cnt"]

    assert _pgc_for(pg_storage, record_id) == first_pgc
    assert pgc_count_before == pgc_count_after
