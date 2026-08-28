import os

import click

from app.fieldapi.command import FieldAPICommand
from app.lib import commands


@click.command(short_help=FieldAPICommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def main(config: str) -> None:
    commands.run(FieldAPICommand(config))
