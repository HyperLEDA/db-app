import os

import click

from app.adminapi.command import AdminAPICommand
from app.lib import commands


@click.command(short_help=AdminAPICommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def adminapi(config: str) -> None:
    commands.run(AdminAPICommand(config))
