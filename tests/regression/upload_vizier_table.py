import uuid

import hyperleda
import hyperleda_scripts
import requests

from app.commands.runtask import RunTaskCommand
from app.lib import commands
from tests import lib


@lib.test_logging_decorator(__file__)
def upload_vizier_table() -> tuple[int, str]:
    table_name = f"vizier_{str(uuid.uuid4())}"
    table_id = hyperleda_scripts.vizier_command(
        "III/258",
        "III/258/fbs",
        hyperleda_table_name=table_name,
        bib_author="Flesch, E.",
        bib_year="2015",
        bib_title="A catalogue of integrated H I fluxes",
        log_level="debug",
        endpoint=hyperleda.DEFAULT_ENDPOINT,
    )
    return table_id, table_name


@lib.test_logging_decorator(__file__)
def check_table_validation(client: hyperleda.HyperLedaClient, table_name: str) -> list[hyperleda.TableValidation]:
    return client.validate_table(table_name).validations or []


@lib.test_logging_decorator(__file__)
def patch_table(client: hyperleda.HyperLedaClient, table_name: str):
    client.patch_table_schema(
        table_name,
        [
            {"type": "change_unit", "column": "RAJ2000", "unit": "hourangle"},
            {"type": "change_unit", "column": "DEJ2000", "unit": "deg"},
        ],
    )


@lib.test_logging_decorator(__file__)
def start_processing(table_id: int):
    commands.run(
        RunTaskCommand(
            "process",
            "configs/dev/tasks.yaml",
            input_data={"table_id": table_id, "batch_size": 200, "workers": 8},
        ),
    )


@lib.test_logging_decorator(__file__)
def check_statuses(client: hyperleda.HyperLedaClient, table_id: int) -> dict[str, int]:
    stats = client.get_table_status_stats(table_id)
    if stats.processing is None:
        raise ValueError("Table was not processed")

    return stats.processing


@lib.test_logging_decorator(__file__)
def layer1_import(table_id: int):
    commands.run(
        RunTaskCommand(
            "layer1-import",
            "configs/dev/tasks.yaml",
            input_data={"table_id": table_id, "batch_size": 50},
        ),
    )


@lib.test_logging_decorator(__file__)
def layer2_import():
    commands.run(
        RunTaskCommand(
            "layer2-import",
            "configs/dev/tasks.yaml",
        ),
    )


@lib.test_logging_decorator(__file__)
def query_objects() -> list[dict]:
    response = requests.get("http://localhost:8081/api/v1/query/simple", params={"name": "1203+668"})
    return response.json().get("data", {}).get("objects", {})


def run():
    client = hyperleda.HyperLedaClient()
    table_id, table_name = upload_vizier_table()

    validations = check_table_validation(client, table_name)
    assert len(validations) != 0

    patch_table(client, table_name)

    validations = check_table_validation(client, table_name)
    assert len(validations) == 0

    start_processing(table_id)

    statuses = check_statuses(client, table_id)
    assert statuses["new"] > 0
    assert statuses.get("existing", 0) == 0
    assert statuses.get("collided", 0) == 0

    layer1_import(table_id)

    layer2_import()

    objects = query_objects()
    assert len(objects) > 0
