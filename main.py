import os

import click

import app.commands.adminapi as adminapi_cmd
import app.commands.dataapi as dataapi_cmd
import app.commands.generate_spec as generate_spec_cmd
import app.commands.importer as importer_cmd
import app.commands.regression_tests as regression_tests_cmd
from app.lib import commands


@click.group()
def cli():
    pass


@cli.command(short_help="Start API server")
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def adminapi(config: str):
    commands.run(adminapi_cmd.AdminAPICommand(config))


@cli.command(short_help="Start Data API server")
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def dataapi(config: str):
    commands.run(dataapi_cmd.DataAPIServer(config))


@cli.command(short_help="Import data from layer 1 to layer 2")
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def importer(config: str):
    commands.run(importer_cmd.ImporterCommand(config))


@cli.command(short_help="Generate OpenAPI spec and write it to file")
@click.option(
    "-o",
    "--output",
    type=str,
    required=True,
    help="Where to put resulting JSON",
)
def generate_spec(output: str):
    commands.run(generate_spec_cmd.GenerateSpecCommand(output))


@cli.command(short_help="Run regression tests")
def regression_tests():
    commands.run(regression_tests_cmd.RegressionTestsCommand())


if __name__ == "__main__":
    cli()
