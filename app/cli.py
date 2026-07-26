import os

import click

from app.commands.adminapi import AdminAPICommand
from app.commands.dataapi import DataAPICommand
from app.lib import commands


@click.group()
def cli() -> None:
    pass


@cli.command(short_help=AdminAPICommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def adminapi(config: str):
    commands.run(AdminAPICommand(config))


@cli.command(short_help=DataAPICommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def dataapi(config: str):
    commands.run(DataAPICommand(config))


@cli.command(
    "serve-tasks",
    short_help="Registers layer2 import Prefect deployments and serves them.",
)
def serve_tasks() -> None:
    # Lazy-load: ServeTasksCommand pulls in Prefect, which slows other commands
    from app.commands.serve_tasks import ServeTasksCommand  # noqa: PLC0415

    commands.run(ServeTasksCommand())
