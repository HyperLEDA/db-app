import os

import click

import app.commands.generate_spec as generate_spec_cmd
import app.commands.regression_tests as regression_tests_command
import app.commands.runserver as runserver_cmd
from app.commands.dataapi import command as dataapi_cmd
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
def runserver(config: str):
    commands.run(runserver_cmd.RunServerCommand(config))


@cli.command(short_help="Start Data API server")
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def dataapi(config: str):
    commands.run(dataapi_cmd.RunDataAPIServer(config))


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
    commands.run(regression_tests_command.RegressionTestsCommand())


if __name__ == "__main__":
    cli()
