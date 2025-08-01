import os
import random
import time
import uuid

import hyperleda
import pandas

from app.commands.runtask import RunTaskCommand
from app.lib import commands
from tests import lib

random.seed(time.time())


@lib.test_logging_decorator(__file__)
def create_marking(client: hyperleda.HyperLedaClient, table_name: str):
    client.create_marking(
        table_name=table_name,
        rules=[
            hyperleda.Catalog(
                name=hyperleda.Name.icrs,
                parameters={
                    "ra": hyperleda.Parameter(column_name="ra"),
                    "dec": hyperleda.Parameter(column_name="dec"),
                    "e_ra": hyperleda.Parameter(column_name="e_ra"),
                    "e_dec": hyperleda.Parameter(column_name="e_dec"),
                },
            ),
            hyperleda.Catalog(
                name=hyperleda.Name.designation,
                parameters={
                    "design": hyperleda.Parameter(column_name="name"),
                },
            ),
        ],
    )


@lib.test_logging_decorator(__file__)
def create_bibliography(client: hyperleda.HyperLedaClient) -> str:
    return client.create_internal_source(
        authors=["Doe, J."],
        title=str(uuid.uuid4()),
        year=2024,
    )


@lib.test_logging_decorator(__file__)
def create_table(client: hyperleda.HyperLedaClient, bib_id: str) -> tuple[int, str]:
    table_name = f"test_{str(uuid.uuid4())}"

    return client.create_table(
        hyperleda.CreateTableRequestSchema(
            table_name,
            [
                hyperleda.ColumnDescription("name", hyperleda.DataType.str, ucd="meta.id"),
                hyperleda.ColumnDescription("ra", hyperleda.DataType.float, "hourangle", "pos.eq.ra"),
                hyperleda.ColumnDescription("dec", hyperleda.DataType.float, "deg", "pos.eq.dec"),
                hyperleda.ColumnDescription("e_ra", hyperleda.DataType.float, "deg"),
                hyperleda.ColumnDescription("e_dec", hyperleda.DataType.float, "deg"),
                hyperleda.ColumnDescription("fuzz", hyperleda.DataType.str),
            ],
            bib_id,
        )
    ), table_name


@lib.test_logging_decorator(__file__)
def upload_data(client: hyperleda.HyperLedaClient, table_id: int):
    df = pandas.DataFrame.from_records(
        [
            {
                "name": f"M {random.randint(1, 1000)}",
                "ra": random.uniform(0, 360),
                "dec": random.uniform(-90, 90),
                "e_ra": 0.1,
                "e_dec": 0.1,
                "fuzz": str(uuid.uuid4()),
            },
            {
                "name": f"M {random.randint(1, 1000)}",
                "ra": random.uniform(0, 360),
                "dec": random.uniform(-90, 90),
                "e_ra": 0.2,
                "e_dec": 0.2,
                "fuzz": str(uuid.uuid4()),
            },
        ]
    )

    client.add_data(table_id, df)


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
def get_object_statuses(client: hyperleda.HyperLedaClient, table_id: int) -> dict[str, int]:
    stats = client.get_table_status_stats(table_id)
    if stats.processing is None:
        raise ValueError("Processing status is None")

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


def run():
    api_host = os.getenv("API_HOST", "localhost")
    api_port = os.getenv("API_PORT", "8080")
    api_url = f"http://{api_host}:{api_port}"

    client = hyperleda.HyperLedaClient(api_url)
    code = create_bibliography(client)
    table_id, table_name = create_table(client, code)
    upload_data(client, table_id)

    create_marking(client, table_name)
    start_processing(table_id)

    statuses_data = get_object_statuses(client, table_id)
    assert statuses_data["new"] == 2

    layer1_import(table_id)
