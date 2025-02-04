import hyperleda
import hyperleda_scripts

from tests import lib


@lib.test_logging_decorator(__file__)
def upload_vizier_table() -> int:
    return hyperleda_scripts.vizier_command("III/258", "III/258/fbs", False)


@lib.test_logging_decorator(__file__)
def start_processing(client: hyperleda.HyperLedaClient, table_id: int):
    client.start_processing(table_id)


@lib.test_logging_decorator(__file__)
def check_statuses(client: hyperleda.HyperLedaClient, table_id: int) -> dict[str, int]:
    stats = client.get_table_status_stats(table_id)
    if stats.processing is None:
        raise ValueError("Table was not processed")

    return stats.processing


def run():
    client = hyperleda.HyperLedaClient()
    table_id = upload_vizier_table()

    start_processing(client, table_id)

    statuses = check_statuses(client, table_id)
    assert statuses["new"] > 0
    assert statuses["processed"] == 0
    assert statuses["collided"] == 0

    # Check object statuses
    # Transfer tables to layer 1
    # Run importer
    # Run layer2 api
    # Query objects from layer 2 api
