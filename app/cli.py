import click

from app.adminapi.cli import main as adminapi
from app.dataapi.cli import main as dataapi
from app.tasks.cli import main as serve_tasks


@click.group()
def cli() -> None:
    pass


cli.add_command(adminapi, name="adminapi")
cli.add_command(dataapi, name="dataapi")
cli.add_command(serve_tasks, name="serve-tasks")
