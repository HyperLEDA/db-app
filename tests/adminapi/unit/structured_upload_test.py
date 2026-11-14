from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest

from app.adminapi.domain.structured_upload import StructuredUploadManager
from app.lib.storage import postgres
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec

_PARAMS = {"table_name": "raw", **{n: f'col("{n}")' for n in ("ra", "dec", "e_ra", "e_dec")}}


def test_start_structured_upload() -> None:
    cols = {
        n: postgres.ColumnInfo(name=n, data_type="double precision", unit="deg", not_null=True)
        for n in ("ra", "dec", "e_ra", "e_dec")
    }
    cols["record_id"] = postgres.ColumnInfo(name="record_id", data_type="uuid", not_null=True)
    repo = mock.Mock()
    repo.get_table_metadata.return_value = postgres.TableInfo(schema="icrs", name="data", columns=cols)
    run_id = uuid4()
    start = mock.Mock(return_value=SimpleNamespace(id=run_id))
    manager = StructuredUploadManager(repo, start_deployment=start)

    assert manager.start(spec.StartStructuredUploadRequest(catalog="icrs", params=_PARAMS)).flow_run_id == str(run_id)
    assert start.call_args.kwargs["name"] == "ICRS/upload-icrs"
    with pytest.raises(NotFoundError):
        manager.start(spec.StartStructuredUploadRequest(catalog="missing", params=_PARAMS))
    with pytest.raises(RuleValidationError):
        manager.start(spec.StartStructuredUploadRequest(catalog="icrs", params={"table_name": "raw"}))
