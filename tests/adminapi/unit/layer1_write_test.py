from unittest import mock

from app.adminapi.domain.layer1_write import Layer1Writer
from app.catalogs import DesignationCatalogObject, ICRSCatalogObject
from app.specs import adminapi


def test_designation_save_normalizes_design() -> None:
    repo = mock.Mock()
    repo.get_column_units.return_value = {}
    writer = Layer1Writer(repo)

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
    writer = Layer1Writer(repo)

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
    writer = Layer1Writer(repo)

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
