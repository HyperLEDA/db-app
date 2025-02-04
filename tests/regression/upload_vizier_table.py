import hyperleda
import hyperleda_scripts

from tests import lib


@lib.test_logging_decorator(__file__)
def upload_vizier_table() -> int:
    return hyperleda_scripts.vizier_command("III/258", "III/258/fbs", False)


@lib.test_logging_decorator(__file__)
def start_processing(client: hyperleda.HyperLedaClient, table_id: int):
    client.start_processing(table_id)


def run():
    client = hyperleda.HyperLedaClient()
    table_id = upload_vizier_table()

    start_processing(client, table_id)

    # Check object statuses
    # Transfer tables to layer 1
    # Run importer
    # Run layer2 api
    # Query objects from layer 2 api
