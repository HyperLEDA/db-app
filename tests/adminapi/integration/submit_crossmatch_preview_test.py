import uuid

import pytest
import structlog

from app.adminapi import model, repository
from app.adminapi.domain.crossmatch import CrossmatchManager
from app.lib.crossmatch.data import write_crossmatch_rows
from app.lib.crossmatch.models import Parameter
from app.lib.storage import enums, postgres
from app.lib.web import errors
from app.specs import adminapi
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def _create_table(repo: repository.Repository, table_name: str) -> None:
    bib_id = repo.create_bibliography(table_name, 2000, ["test"], "test")
    repo.create_table(
        model.Layer0TableMeta(
            postgres.TableInfo(schema=repository.RAWDATA_SCHEMA, name=table_name),
            bib_id,
        )
    )


def test_preview_submit_crossmatch_does_not_write(
    pg_storage: PostgresTestStorage,
) -> None:
    storage = pg_storage.get_storage()
    repo = repository.Repository(storage, structlog.get_logger())
    table_name = "submit_preview"
    new_id = str(uuid.uuid4())
    existing_id = str(uuid.uuid4())
    pending_id = str(uuid.uuid4())
    collided_id = str(uuid.uuid4())
    assigned_id = str(uuid.uuid4())
    _create_table(repo, table_name)
    with repo.with_tx():
        repo.register_records(table_name, [new_id, existing_id, pending_id, collided_id, assigned_id])
    repo.register_pgcs([7, 8, 9])
    with repo.with_tx():
        write_crossmatch_rows(
            storage,
            [
                (new_id, enums.RecordTriageStatus.RESOLVED, []),
                (
                    existing_id,
                    enums.RecordTriageStatus.RESOLVED,
                    [(7, {Parameter.COORDINATES: True, Parameter.NAME: False})],
                ),
                (pending_id, enums.RecordTriageStatus.PENDING, []),
                (collided_id, enums.RecordTriageStatus.RESOLVED, [8, 9]),
                (assigned_id, enums.RecordTriageStatus.RESOLVED, [7]),
            ],
        )
    storage.exec("UPDATE layer0.records SET pgc = 7 WHERE id = %s", params=[assigned_id])

    response = CrossmatchManager(repo).preview_submit(
        adminapi.PreviewSubmitCrossmatchRequest(table_name=table_name, sample_size=20)
    )

    assert (response.sample_count, response.new_count, response.existing_count) == (2, 1, 1)
    by_id = {row.record_id: row for row in response.rows}
    assert set(by_id) == {new_id, existing_id}
    assert by_id[new_id].outcome == "new" and by_id[new_id].pgc is None
    assert by_id[new_id].parameters == adminapi.PreviewCrossmatchParameters()
    assert by_id[existing_id].outcome == "existing" and by_id[existing_id].pgc == 7
    assert by_id[existing_id].parameters == adminapi.PreviewCrossmatchParameters(
        coordinates=True, name=False
    )
    assert storage.query_one("SELECT pgc FROM layer0.records WHERE id = %s", params=[new_id])["pgc"] is None


def test_preview_submit_crossmatch_missing_table(pg_storage: PostgresTestStorage) -> None:
    repo = repository.Repository(pg_storage.get_storage(), structlog.get_logger())
    with pytest.raises(errors.NotFoundError):
        CrossmatchManager(repo).preview_submit(adminapi.PreviewSubmitCrossmatchRequest(table_name="missing"))
