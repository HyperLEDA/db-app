from unittest import mock
from uuid import uuid4

import pytest

from app.adminapi.domain.structured_upload import StructuredUploadManager
from app.lib.web.errors import NotFoundError
from app.specs import adminapi as spec


def test_start_structured_upload() -> None:
    run_id = str(uuid4())
    prefect = mock.Mock()
    prefect.create_flow_run.return_value = run_id
    manager = StructuredUploadManager(prefect)
    params = {"table_name": "raw", "ra": 'col("ra")'}

    assert manager.start(spec.StartStructuredUploadRequest(catalog="icrs", params=params)).flow_run_id == run_id
    prefect.create_flow_run.assert_called_once_with(
        name="ICRS/upload-icrs",
        parameters={"params": params},
    )
    with pytest.raises(NotFoundError):
        manager.start(spec.StartStructuredUploadRequest(catalog="missing", params=params))
