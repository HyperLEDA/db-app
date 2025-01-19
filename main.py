import os

import click

import app.commands.generate_spec as generate_spec_cmd
import app.commands.runserver as runserver_cmd
from app.lib import commands
from tests.regression import upload_simple_table


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
    commands.run(
        runserver_cmd.RunServerCommand(config),
    )


@cli.command(short_help="Generate OpenAPI spec and write it to file")
@click.option("-o", "--output", type=str, required=True, help="Where to put resulting JSON")
def generate_spec(output: str):
    generate_spec_cmd.generate_spec(output)


@cli.command(short_help="Run regression tests")
def regression_tests():
    upload_simple_table.run()


if __name__ == "__main__":
    cli()
