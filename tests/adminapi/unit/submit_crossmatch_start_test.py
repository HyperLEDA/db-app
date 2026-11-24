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
        parameters={
            "params": {
                "table_name": "raw",
                "row_filter": "",
                "include_new": True,
                "include_existing": True,
                "require_parameters": [],
                "batch_size": 5000,
            }
        },
    )
    with pytest.raises(RuleValidationError):
        manager.start_submit(adminapi.StartSubmitCrossmatchRequest(params={"batch_size": 10}))
    with pytest.raises(RuleValidationError):
        manager.start_submit(
            adminapi.StartSubmitCrossmatchRequest(
                params={"table_name": "raw", "include_new": False, "include_existing": False}
            )
        )


def test_submit_crossmatch_drops_required_parameters_without_existing() -> None:
    params = adminapi.SubmitCrossmatchParams.model_validate(
        {"table_name": "raw", "include_existing": False, "require_parameters": ["name", "name"]}
    )
    assert params.require_parameters == []
