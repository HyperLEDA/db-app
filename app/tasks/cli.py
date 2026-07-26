import click

from app.lib import commands
from app.tasks.command import ServeTasksCommand


@click.command(short_help="Registers layer2 import Prefect deployments and serves them.")
def main() -> None:
    commands.run(ServeTasksCommand())
