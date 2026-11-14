from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest

from app.adminapi.domain.structured_upload import StructuredUploadManager
from app.lib.web.errors import NotFoundError
from app.specs import adminapi as spec


def test_start_structured_upload() -> None:
    run_id = uuid4()
    start = mock.Mock(return_value=SimpleNamespace(id=run_id))
    manager = StructuredUploadManager(prefect_api_url="http://tasks:4200/api", start_deployment=start)
    params = {"table_name": "raw", "ra": 'col("ra")'}

    assert manager.start(spec.StartStructuredUploadRequest(catalog="icrs", params=params)).flow_run_id == str(run_id)
    assert start.call_args.kwargs == {
        "name": "ICRS/upload-icrs",
        "parameters": {"params": params},
        "timeout": 0,
    }
    with pytest.raises(NotFoundError):
        manager.start(spec.StartStructuredUploadRequest(catalog="missing", params=params))
