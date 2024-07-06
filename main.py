import click

import app.commands.generate_spec as generate_spec_cmd
import app.commands.runserver as runserver_cmd


@click.group()
def cli():
    pass


@cli.command(short_help="Start API server")
@click.option("-c", "--config", type=str, required=True, help="Path to configuration file")
def runserver(config: str):
    runserver_cmd.start(config)


@cli.command(short_help="Generate OpenAPI spec and write it to file")
@click.option("-o", "--output", type=str, required=True, help="Where to put resulting JSON")
def generate_spec(output: str):
    generate_spec_cmd.generate_spec(output)


if __name__ == "__main__":
    cli()
