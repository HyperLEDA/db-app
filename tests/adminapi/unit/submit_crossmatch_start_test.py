from unittest import mock

import pytest

from app.adminapi.domain.crossmatch import CrossmatchManager
from app.lib.web.errors import RuleValidationError
from app.specs import adminapi


def test_start_submit_crossmatch() -> None:
    prefect = mock.Mock()
    prefect.create_flow_run.return_value = "run-1"
    manager = CrossmatchManager(mock.Mock(), prefect)
    assert manager.start_submit(adminapi.StartSubmitCrossmatchRequest(params={"table_name": "raw"})).task_id == "run-1"
    prefect.create_flow_run.assert_called_once_with(
        name="Submit crossmatch/submit-crossmatch",
        parameters={"params": {"table_name": "raw", "batch_size": 1000}},
    )
    with pytest.raises(RuleValidationError):
        manager.start_submit(adminapi.StartSubmitCrossmatchRequest(params={"batch_size": 10}))
