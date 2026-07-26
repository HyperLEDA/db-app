import os

import click

from app.commands.adminapi import AdminAPICommand
from app.commands.dataapi import DataAPICommand
from app.commands.generate_spec import GenerateSpecCommand
from app.commands.runtask import RunTaskCommand
from app.lib import commands


@click.group()
@click.option(
    "--log-level",
    type=click.Choice(["debug", "info", "warning", "error", "critical"], case_sensitive=False),
    default="info",
    help="Set the logging level (for runtask and other commands that use it)",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level


@cli.command(short_help=AdminAPICommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def adminapi(config: str):
    commands.run(AdminAPICommand(config))


@cli.command(short_help=DataAPICommand.help())
@click.option(
    "-c",
    "--config",
    type=str,
    default=lambda: os.environ.get("CONFIG", ""),
    help="Path to configuration file",
)
def dataapi(config: str):
    commands.run(DataAPICommand(config))


@cli.command(short_help=RunTaskCommand.help(), context_settings={"ignore_unknown_options": True})
@click.argument(
    "task_name",
    required=True,
    type=str,
)
@click.option(
    "-i",
    "--input-data",
    type=str,
    help="Path to input data file",
)
@click.pass_context
@click.argument("task_args", nargs=-1, type=click.UNPROCESSED)
def runtask(
    ctx: click.Context,
    task_name: str,
    input_data: str | None,
    task_args: tuple[str, ...],
) -> None:
    log_level = (ctx.obj or {}).get("log_level", "info")
    commands.run(RunTaskCommand(task_name, input_data, None, task_args, log_level))


@cli.command(short_help=GenerateSpecCommand.help())
@click.option(
    "-o",
    "--output",
    type=str,
    required=True,
    help="Where to put resulting JSON",
)
def generate_spec(output: str):
    commands.run(GenerateSpecCommand(output))


@cli.command(
    "serve-tasks",
    short_help="Registers layer2 import Prefect deployments and serves them.",
)
def serve_tasks() -> None:
    # Lazy-load: ServeTasksCommand pulls in Prefect, which slows other commands
    from app.commands.serve_tasks import ServeTasksCommand  # noqa: PLC0415

    commands.run(ServeTasksCommand())
