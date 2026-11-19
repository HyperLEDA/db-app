import pytest
import structlog

from app.adminapi import repository
from app.adminapi.domain.crossmatch import CrossmatchManager
from app.lib.storage import postgres
from app.specs import adminapi
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def _seed(storage: postgres.PgStorage, table_name: str) -> None:
    bib_id = layer_seed.create_bibliography(storage, f"bib-{table_name}", 2000, ["test"], "test")
    layer_seed.create_table(storage, table_name, bib_id)
    layer_seed.register_records(storage, table_name, ["near", "far"])
    layer_seed.register_pgcs(storage, [100])
    layer_seed.save_structured_data(
        storage,
        "icrs.data",
        ["ra", "e_ra", "dec", "e_dec"],
        ["near", "far"],
        [[10.0, 0.1, 20.0, 0.1], [180.0, 0.1, 0.0, 0.1]],
    )
    storage.exec(
        "INSERT INTO layer2.objects (pgc, name, ra, dec) VALUES (%s, %s, %s, %s)",
        params=[100, "NGC 1", 10.0, 20.0],
    )
    storage.exec(
        "UPDATE layer0.tables SET modification_dt = TIMESTAMP '2000-01-01' WHERE table_name = %s",
        params=[table_name],
    )


def test_preview_crossmatch_does_not_write(pg_storage: PostgresTestStorage) -> None:
    storage = pg_storage.get_storage()
    table_name = "xmatch_preview"
    _seed(storage, table_name)
    repo = repository.Repository(storage, structlog.get_logger())

    response = CrossmatchManager(repo).preview(adminapi.PreviewCrossmatchRequest(table_name=table_name, radius=30))

    by_status = {stat.status: stat for stat in response.statistics}
    assert response.total_count == 2
    assert response.eligible_count == 2
    assert response.sample_count == 2
    assert set(by_status) == {"existing", "new"}
    assert by_status["existing"].triage == "pending" and by_status["existing"].count == 1
    assert by_status["new"].triage == "resolved" and by_status["new"].count == 1
    existing_row = by_status["existing"].rows[0]
    assert existing_row.record_id == "near" and existing_row.candidates == [100]
    assert existing_row.neighbors[0].pgc == 100
    assert existing_row.neighbors[0].ra == 10.0 and existing_row.neighbors[0].dec == 20.0
    assert by_status["new"].rows[0].record_id == "far" and by_status["new"].rows[0].candidates == []
    assert by_status["existing"].parameters.coordinates is True
    assert by_status["existing"].parameters.name is False
    assert storage.query("SELECT record_id FROM layer0.crossmatch") == []
    modified = storage.query_one(
        "SELECT modification_dt FROM layer0.tables WHERE table_name = %s",
        params=[table_name],
    )
    assert modified["modification_dt"].year == 2000
