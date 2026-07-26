import click

from app.adminapi.cli import adminapi
from app.dataapi.cli import dataapi
from app.tasks.cli import serve_tasks


@click.group()
def cli() -> None:
    pass


cli.add_command(adminapi)
cli.add_command(dataapi)
cli.add_command(serve_tasks)
