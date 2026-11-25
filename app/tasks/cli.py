import click

from app.lib import commands
from app.tasks.command import TasksWorkerCommand


@click.command(short_help="Registers async tasks for Leda.")
def main() -> None:
    commands.run(TasksWorkerCommand())
