import os
import random
import time
import uuid

import hyperleda
import pandas

from app.commands.processor.command import ProcessorCommand
from app.lib import commands
from tests import lib

random.seed(time.time())


@lib.test_logging_decorator(__file__)
def create_bibliography(client: hyperleda.HyperLedaClient) -> str:
    return client.create_internal_source(
        authors=["Doe, J."],
        title=str(uuid.uuid4()),
        year=2024,
    )


@lib.test_logging_decorator(__file__)
def create_table(client: hyperleda.HyperLedaClient, bib_id: str) -> int:
    return client.create_table(
        hyperleda.CreateTableRequestSchema(
            f"test_{str(uuid.uuid4())}",
            [
                hyperleda.ColumnDescription("name", hyperleda.DataType.str, ucd="meta.id"),
                hyperleda.ColumnDescription("ra", hyperleda.DataType.float, "hourangle", "pos.eq.ra"),
                hyperleda.ColumnDescription("dec", hyperleda.DataType.float, "deg", "pos.eq.dec"),
                hyperleda.ColumnDescription("fuzz", hyperleda.DataType.str),
            ],
            bib_id,
        )
    )


@lib.test_logging_decorator(__file__)
def upload_data(client: hyperleda.HyperLedaClient, table_id: int):
    df = pandas.DataFrame.from_records(
        [
            {
                "name": f"M {random.randint(1, 1000)}",
                "ra": random.uniform(0, 360),
                "dec": random.uniform(-90, 90),
                "fuzz": str(uuid.uuid4()),
            },
            {
                "name": f"M {random.randint(1, 1000)}",
                "ra": random.uniform(0, 360),
                "dec": random.uniform(-90, 90),
                "fuzz": str(uuid.uuid4()),
            },
        ]
    )

    client.add_data(table_id, df)


@lib.test_logging_decorator(__file__)
def start_processing(table_id: int):
    commands.run(ProcessorCommand("configs/dev/processor.yaml", table_id=table_id, batch_size=200, workers=8))


@lib.test_logging_decorator(__file__)
def get_object_statuses(client: hyperleda.HyperLedaClient, table_id: int) -> dict[str, int]:
    stats = client.get_table_status_stats(table_id)
    if stats.processing is None:
        raise ValueError("Processing status is None")

    return stats.processing


@lib.test_logging_decorator(__file__)
def set_table_status(client: hyperleda.HyperLedaClient, table_id: int):
    client.set_table_status(table_id)


def run():
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8080")
    api_url = f"http://{api_host}:{api_port}"

    client = hyperleda.HyperLedaClient(api_url)

    code = create_bibliography(client)
    table_id = create_table(client, code)

    upload_data(client, table_id)
    start_processing(table_id)

    statuses_data = get_object_statuses(client, table_id)
    assert statuses_data["new"] == 2

    set_table_status(client, table_id)
