from unittest import mock

import pytest

from app.adminapi.domain.crossmatch import CrossmatchManager
from app.lib.web.errors import RuleValidationError
from app.specs import adminapi


def test_start_crossmatch() -> None:
    prefect = mock.Mock()
    prefect.create_flow_run.return_value = "run-1"
    manager = CrossmatchManager(mock.Mock(), prefect)
    params = {"table_name": "raw", "radius": 5.0}

    assert manager.start(adminapi.StartCrossmatchRequest(params=params)).task_id == "run-1"
    prefect.create_flow_run.assert_called_once_with(
        name="Crossmatch/crossmatch",
        parameters={
            "params": {
                "table_name": "raw",
                "include_pgc": False,
                "include_redshift": False,
                "include_nature": False,
                "radius": 5.0,
                "pgc_column": "",
                "redshift_tolerance": 0.0,
                "row_filter": "",
                "batch_size": 1000,
            }
        },
    )
    with pytest.raises(RuleValidationError):
        manager.start(adminapi.StartCrossmatchRequest(params={"table_name": "raw"}))
