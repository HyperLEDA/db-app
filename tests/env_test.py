import app.adminapi.command as adminapi
import app.dataapi.command as dataapi
import app.fieldapi.command as fieldapi


def test_parse_adminapi_config() -> None:
    _ = adminapi.parse_config("configs/dev/adminapi.yaml")


def test_parse_dataapi_config() -> None:
    _ = dataapi.parse_config("configs/dev/dataapi.yaml")


def test_parse_fieldapi_config() -> None:
    _ = fieldapi.parse_config("configs/dev/fieldapi.yaml")
