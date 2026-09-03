import pytest

import app.adminapi.command as adminapi
import app.dataapi.command as dataapi
import app.fieldapi.command as fieldapi


@pytest.mark.parametrize(
    "path",
    [
        "configs/dev/adminapi.yaml",
        "configs/test/adminapi.yaml",
        "configs/prod/adminapi.yaml",
    ],
)
def test_parse_adminapi_config(path: str) -> None:
    _ = adminapi.parse_config(path)


@pytest.mark.parametrize(
    "path",
    [
        "configs/dev/dataapi.yaml",
        "configs/test/dataapi.yaml",
        "configs/prod/dataapi.yaml",
    ],
)
def test_parse_dataapi_config(path: str) -> None:
    _ = dataapi.parse_config(path)


@pytest.mark.parametrize(
    "path",
    [
        "configs/dev/fieldapi.yaml",
        "configs/test/fieldapi.yaml",
        "configs/prod/fieldapi.yaml",
    ],
)
def test_parse_fieldapi_config(path: str) -> None:
    _ = fieldapi.parse_config(path)
