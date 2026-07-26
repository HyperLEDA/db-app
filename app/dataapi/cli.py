import os

import click

from app.dataapi.command import DataAPICommand
from app.lib import commands


@click.command(short_help=DataAPICommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def main(config: str) -> None:
    commands.run(DataAPICommand(config))
