import click

from app.lib import commands


@click.command(
    "serve-tasks",
    short_help="Registers layer2 import Prefect deployments and serves them.",
)
def serve_tasks() -> None:
    # Lazy-load: ServeTasksCommand pulls in Prefect, which slows other commands
    from app.tasks.command import ServeTasksCommand  # noqa: PLC0415

    commands.run(ServeTasksCommand())
