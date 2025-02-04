import uuid

import hyperleda
import hyperleda_scripts

from tests import lib


@lib.test_logging_decorator(__file__)
def upload_vizier_table() -> int:
    return hyperleda_scripts.vizier_command(
        "III/258", "III/258/fbs", hyperleda_table_name=f"vizier_{str(uuid.uuid4())}"
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
    assert ("existing" not in statuses) or (statuses["existing"] == 0)
    assert ("collided" not in statuses) or (statuses["collided"] == 0)

    set_table_status(client, table_id)
    # Transfer tables to layer 1
    # Run importer
    # Run layer2 api
    # Query objects from layer 2 api
