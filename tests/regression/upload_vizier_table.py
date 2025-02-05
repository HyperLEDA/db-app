import uuid

import hyperleda
import hyperleda_scripts
import requests

from app.commands.importer.command import ImporterCommand
from app.lib import commands
from tests import lib


@lib.test_logging_decorator(__file__)
def upload_vizier_table() -> int:
    return hyperleda_scripts.vizier_command(
        "III/258",
        "III/258/fbs",
        hyperleda_table_name=f"vizier_{str(uuid.uuid4())}",
        bib_author="Flesch, E.",
        bib_year="2015",
        bib_title="A catalogue of integrated H I fluxes",
        log_level="warn",
    )


@lib.test_logging_decorator(__file__)
def check_table_validation(client: hyperleda.HyperLedaClient, table_id: int) -> list[hyperleda.TableValidation]:
    return client.validate_table(table_id).validations or []


@lib.test_logging_decorator(__file__)
def patch_table(client: hyperleda.HyperLedaClient, table_id: int):
    client.patch_table_schema(
        table_id,
        [
            {"type": "change_unit", "column": "RAJ2000", "unit": "hourangle"},
            {"type": "change_unit", "column": "DEJ2000", "unit": "deg"},
        ],
    )


@lib.test_logging_decorator(__file__)
def start_processing(client: hyperleda.HyperLedaClient, table_id: int):
    client.start_processing(table_id)


@lib.test_logging_decorator(__file__)
def check_statuses(client: hyperleda.HyperLedaClient, table_id: int) -> dict[str, int]:
    stats = client.get_table_status_stats(table_id)
    if stats.processing is None:
        raise ValueError("Table was not processed")

    return stats.processing


@lib.test_logging_decorator(__file__)
def set_table_status(client: hyperleda.HyperLedaClient, table_id: int):
    client.set_table_status(table_id)


@lib.test_logging_decorator(__file__)
def run_importer():
    commands.run(ImporterCommand("configs/dev/importer.yaml"))


@lib.test_logging_decorator(__file__)
def query_objects() -> list[dict]:
    response = requests.get("http://localhost:8081/api/v1/query/simple", params={"name": "1203+668"})
    return response.json().get("data", {}).get("objects", {})


def run():
    client = hyperleda.HyperLedaClient()
    table_id = upload_vizier_table()

    validations = check_table_validation(client, table_id)
    assert len(validations) != 0

    patch_table(client, table_id)

    validations = check_table_validation(client, table_id)
    assert len(validations) == 0

    start_processing(client, table_id)

    statuses = check_statuses(client, table_id)
    assert statuses["new"] > 0
    assert statuses.get("existing", 0) == 0
    assert statuses.get("collided", 0) == 0

    set_table_status(client, table_id)

    run_importer()

    objects = query_objects()
    assert len(objects) > 0
