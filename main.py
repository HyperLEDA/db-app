import os

import click

from app.commands.adminapi import AdminAPICommand
from app.commands.dataapi import DataAPICommand
from app.commands.generate_spec import GenerateSpecCommand
from app.commands.importer import ImporterCommand
from app.commands.processor import ProcessorCommand
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


@cli.command(short_help=ImporterCommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def importer(config: str):
    commands.run(ImporterCommand(config))


@cli.command(short_help=ProcessorCommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
@click.argument(
    "table_id",
    required=True,
    type=int,
)
@click.option(
    "-b",
    "--batch-size",
    type=int,
    default=1000,
    help="Batch size for processing",
)
def processor(config: str, table_id: int, batch_size: int):
    commands.run(ProcessorCommand(config, table_id, batch_size))


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
