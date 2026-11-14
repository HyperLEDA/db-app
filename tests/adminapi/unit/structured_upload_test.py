from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest

from app.adminapi.domain.structured_upload import StructuredUploadManager
from app.lib.storage import postgres
from app.lib.web.errors import NotFoundError, RuleValidationError
from app.specs import adminapi as spec


def _col(name: str, data_type: str, *, unit: str | None = None, not_null: bool = True) -> postgres.ColumnInfo:
    return postgres.ColumnInfo(name=name, data_type=data_type, unit=unit, not_null=not_null)


def _icrs_table() -> postgres.TableInfo:
    return postgres.TableInfo(
        schema="icrs",
        name="data",
        columns={
            "record_id": _col("record_id", "uuid"),
            "ra": _col("ra", "double precision", unit="deg"),
            "dec": _col("dec", "double precision", unit="deg"),
            "e_ra": _col("e_ra", "double precision", unit="deg"),
            "e_dec": _col("e_dec", "double precision", unit="deg"),
        },
    )


def test_start_structured_upload_runs_deployment() -> None:
    repo = mock.Mock()
    repo.get_table_metadata.return_value = _icrs_table()
    flow_run_id = uuid4()
    start_deployment = mock.Mock(return_value=SimpleNamespace(id=flow_run_id))
    manager = StructuredUploadManager(repo, start_deployment=start_deployment)

    response = manager.start(
        spec.StartStructuredUploadRequest(
            catalog="icrs",
            params={
                "table_name": "raw_table",
                "ra": 'col("ra") * deg',
                "dec": 'col("dec") * deg',
                "e_ra": 'col("e_ra") * deg',
                "e_dec": 'col("e_dec") * deg',
                "write": False,
                "batch_size": 1000,
            },
        )
    )

    assert response.flow_run_id == str(flow_run_id)
    start_deployment.assert_called_once()
    call_kwargs = start_deployment.call_args.kwargs
    assert call_kwargs["name"] == "ICRS/upload-icrs"
    assert call_kwargs["timeout"] == 0
    assert call_kwargs["parameters"]["params"]["table_name"] == "raw_table"
    assert call_kwargs["parameters"]["params"]["write"] is False
    assert call_kwargs["parameters"]["params"]["batch_size"] == 1000
    repo.get_table_metadata.assert_called_once_with("icrs", "data")


def test_start_structured_upload_unknown_catalog() -> None:
    manager = StructuredUploadManager(mock.Mock(), start_deployment=mock.Mock())
    with pytest.raises(NotFoundError):
        manager.start(spec.StartStructuredUploadRequest(catalog="missing", params={"table_name": "t"}))


def test_start_structured_upload_invalid_params() -> None:
    repo = mock.Mock()
    repo.get_table_metadata.return_value = _icrs_table()
    start_deployment = mock.Mock()
    manager = StructuredUploadManager(repo, start_deployment=start_deployment)

    with pytest.raises(RuleValidationError):
        manager.start(
            spec.StartStructuredUploadRequest(
                catalog="icrs",
                params={"table_name": "raw_table"},
            )
        )

    start_deployment.assert_not_called()
