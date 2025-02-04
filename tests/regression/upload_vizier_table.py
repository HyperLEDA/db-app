import hyperleda
import hyperleda_scripts

from tests import lib


@lib.test_logging_decorator(__file__)
def upload_vizier_table() -> int:
    return hyperleda_scripts.vizier_command("III/258", "III/258/fbs", False)


def run():
    client = hyperleda.HyperLedaClient()
    table_id = upload_vizier_table()

    # Start processing
    # Check object statuses
    # Transfer tables to layer 1
    # Run importer
    # Run layer2 api
    # Query objects from layer 2 api
