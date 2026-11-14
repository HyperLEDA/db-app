from unittest import mock
from uuid import uuid4

import pytest

from app.adminapi.domain.layer1_write import Layer1Writer
from app.catalogs.layer1 import DesignationCatalogObject, ICRSCatalogObject
from app.lib.web.errors import NotFoundError
from app.specs import adminapi


def test_designation_save_normalizes_design() -> None:
    repo = mock.Mock()
    repo.get_column_units.return_value = {}
    writer = Layer1Writer(repo, mock.Mock())

    request = adminapi.SaveStructuredDataRequest(
        catalog="designation",
        columns=["design"],
        ids=["r1"],
        data=[["ngc905"]],
    )
    writer.save_data(request)

    repo.save_structured_data.assert_called_once_with(
        DesignationCatalogObject.layer1_table(),
        ["design"],
        ["r1"],
        [["NGC 905"]],
        conflict_keys=DesignationCatalogObject.layer1_primary_keys(),
    )


def test_designation_save_preserves_already_normalized_design() -> None:
    repo = mock.Mock()
    repo.get_column_units.return_value = {}
    writer = Layer1Writer(repo, mock.Mock())

    request = adminapi.SaveStructuredDataRequest(
        catalog="designation",
        columns=["design"],
        ids=["r1"],
        data=[["NGC 905"]],
    )
    writer.save_data(request)

    repo.save_structured_data.assert_called_once_with(
        DesignationCatalogObject.layer1_table(),
        ["design"],
        ["r1"],
        [["NGC 905"]],
        conflict_keys=DesignationCatalogObject.layer1_primary_keys(),
    )


def test_non_designation_save_is_unaffected() -> None:
    repo = mock.Mock()
    repo.get_column_units.return_value = {"ra": "deg", "dec": "deg"}
    writer = Layer1Writer(repo, mock.Mock())

    request = adminapi.SaveStructuredDataRequest(
        catalog="icrs",
        columns=["ra", "dec"],
        units={"ra": "deg", "dec": "deg"},
        ids=["r1"],
        data=[[12.1, 0.1]],
    )
    writer.save_data(request)

    repo.save_structured_data.assert_called_once_with(
        ICRSCatalogObject.layer1_table(),
        ["ra", "dec"],
        ["r1"],
        [[12.1, 0.1]],
        conflict_keys=ICRSCatalogObject.layer1_primary_keys(),
    )


def test_start_upload() -> None:
    run_id = str(uuid4())
    prefect = mock.Mock()
    prefect.create_flow_run.return_value = run_id
    writer = Layer1Writer(mock.Mock(), prefect)
    params = {"table_name": "raw", "ra": 'col("ra")'}

    assert (
        writer.start_upload(adminapi.StartStructuredUploadRequest(catalog="icrs", params=params)).task_id == run_id
    )
    prefect.create_flow_run.assert_called_once_with(
        name="ICRS/upload-icrs",
        parameters={"params": params},
    )
    with pytest.raises(NotFoundError):
        writer.start_upload(adminapi.StartStructuredUploadRequest(catalog="missing", params=params))
