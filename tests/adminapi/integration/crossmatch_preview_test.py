import pytest
import structlog

from app.adminapi import repository
from app.adminapi.domain.crossmatch import CrossmatchManager
from app.specs import adminapi
from tests.lib import layer_seed
from tests.lib.postgres import PostgresTestStorage

pytestmark = pytest.mark.usefixtures("cleared_pg_storage")


def test_preview_crossmatch_does_not_write(pg_storage: PostgresTestStorage) -> None:
    storage = pg_storage.get_storage()
    table_name = "xmatch_preview"
    layer_seed.seed_crossmatch_preview_table(storage, table_name)
    response = CrossmatchManager(repository.Repository(storage, structlog.get_logger())).preview(
        adminapi.PreviewCrossmatchRequest(table_name=table_name, radius_arcsec=30)
    )
    by_status = {stat.status: stat for stat in response.statistics}
    assert (response.total_count, response.eligible_count, response.sample_count) == (2, 2, 2)
    assert set(by_status) == {"existing", "new"}
    assert by_status["existing"].triage == "pending" and by_status["existing"].count == 1
    assert by_status["new"].triage == "resolved" and by_status["new"].count == 1
    existing_row = by_status["existing"].rows[0]
    assert existing_row.record_id == "near" and existing_row.candidates == [100]
    assert existing_row.neighbors[0].pgc == 100
    assert existing_row.neighbors[0].ra == 10.0
    assert existing_row.neighbors[0].dec == 20.0
    assert by_status["new"].rows[0].record_id == "far"
    assert by_status["new"].rows[0].candidates == []
    assert by_status["existing"].parameters.coordinates is True and by_status["existing"].parameters.name is False
    assert storage.query("SELECT record_id FROM layer0.crossmatch") == []
    modified = storage.query_one(
        "SELECT modification_dt FROM layer0.tables WHERE table_name = %s",
        params=[table_name],
    )
    assert modified["modification_dt"].year == 2000
