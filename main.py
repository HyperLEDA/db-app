import click

import app.commands.runserver as runserver_cmd


@click.group()
def cli():
    pass


@cli.command(short_help="Start API server")
@click.option("-c", "--config", type=str, required=True, help="Path to configuration file")
def runserver(config: str):
    runserver_cmd.start(config)


if __name__ == "__main__":
    cli()
