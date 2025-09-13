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
            hyperleda.CatalogToMark(
                name="icrs",
                parameters={
                    "ra": hyperleda.ParameterToMark(column_name="ra"),
                    "dec": hyperleda.ParameterToMark(column_name="dec"),
                    "e_ra": hyperleda.ParameterToMark(column_name="e_ra"),
                    "e_dec": hyperleda.ParameterToMark(column_name="e_dec"),
                },
                key=None,
                additional_params=None,
            ),
            hyperleda.CatalogToMark(
                name="designation",
                parameters={
                    "design": hyperleda.ParameterToMark(column_name="name"),
                },
                key=None,
                additional_params=None,
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
        hyperleda.CreateTableRequest(
            table_name=table_name,
            columns=[
                hyperleda.ColumnDescription(
                    name="name", data_type=hyperleda.DatatypeEnum.str, ucd="meta.id", unit=None, description=None
                ),
                hyperleda.ColumnDescription(
                    name="ra",
                    data_type=hyperleda.DatatypeEnum.float,
                    unit="hourangle",
                    ucd="pos.eq.ra",
                    description=None,
                ),
                hyperleda.ColumnDescription(
                    name="dec", data_type=hyperleda.DatatypeEnum.float, unit="deg", ucd="pos.eq.dec", description=None
                ),
                hyperleda.ColumnDescription(
                    name="e_ra", data_type=hyperleda.DatatypeEnum.float, unit="deg", ucd=None, description=None
                ),
                hyperleda.ColumnDescription(
                    name="e_dec", data_type=hyperleda.DatatypeEnum.float, unit="deg", ucd=None, description=None
                ),
                hyperleda.ColumnDescription(
                    name="fuzz", data_type=hyperleda.DatatypeEnum.str, ucd=None, unit=None, description=None
                ),
            ],
            bibcode=bib_id,
            datatype=hyperleda.DataType.regular,
            description="",
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
def start_processing(table_id: int, table_name: str):
    commands.run(
        RunTaskCommand(
            "process",
            "configs/dev/tasks.yaml",
            input_data={"table_id": table_id, "batch_size": 200, "workers": 8},
        ),
    )

    commands.run(
        RunTaskCommand(
            "crossmatch",
            "configs/dev/tasks.yaml",
            input_data={"table_name": table_name},
        ),
    )


@lib.test_logging_decorator(__file__)
def get_object_statuses(client: hyperleda.HyperLedaClient, table_name: str) -> dict[str, int]:
    table_info = client.get_table(table_name)
    if table_info.statistics is None:
        raise ValueError("Processing status is None")

    return table_info.statistics


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
    start_processing(table_id, table_name)

    statuses_data = get_object_statuses(client, table_name)
    assert statuses_data["new"] == 2

    layer1_import(table_id)
