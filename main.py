import os

import click

from app.commands.adminapi import AdminAPICommand
from app.commands.dataapi import DataAPICommand
from app.commands.generate_spec import GenerateSpecCommand
from app.commands.runtask import RunTaskCommand
from app.lib import commands


@click.group()
def cli():
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


@cli.command(short_help=RunTaskCommand.help(), context_settings={"ignore_unknown_options": True})
@click.argument(
    "task_name",
    required=True,
    type=str,
)
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
@click.option(
    "-i",
    "--input-data",
    type=str,
    help="Path to input data file",
)
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error", "critical"], case_sensitive=False),
    default="info",
    help="Set the logging level",
)
@click.argument("task_args", nargs=-1, type=click.UNPROCESSED)
def runtask(task_name: str, config: str, input_data: str | None, log_level: str, task_args: tuple[str, ...]):
    commands.run(RunTaskCommand(task_name, config, input_data, None, task_args, log_level))


@cli.command(short_help=GenerateSpecCommand.help())
@click.option(
    "-o",
    "--output",
    type=str,
    required=True,
    help="Where to put resulting JSON",
)
def generate_spec(output: str):
    commands.run(GenerateSpecCommand(output))


if __name__ == "__main__":
    cli()
