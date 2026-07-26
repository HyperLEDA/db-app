import datetime
import logging
import os
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

import structlog
from prefect import flow
from prefect.deployments.runner import RunnerDeployment
from prefect.flows import Flow
from prefect.logging import get_run_logger
from pydantic import Field

from app import tasks

LAYER2_TASK_NAMES: tuple[str, ...] = (
    "layer2-import",
    "layer2-import-designation",
    "layer2-import-icrs",
    "layer2-import-redshift",
    "layer2-import-nature",
)

BATCH_SIZE_DESCRIPTION = "Number of rows in a single query"
DRY_RUN_DESCRIPTION = (
    "Calculate all values but do not write them to the database. Useful to test changes in the task itself."
)
SINCE_DESCRIPTION = (
    "If set, upload all PGC objects that were updated since that time. "
    "If not set, will use timestamp of the last update."
)
CLEANUP_ORPHANS_DESCRIPTION = (
    "Remove PGC objects that were left without corresponding records. "
    "Useful if any records were deleted or changed PGC numbers since the last update."
)
CATALOGS_DESCRIPTION = "Catalogs to import: designation, icrs, redshift, nature. If not set, imports all."

BATCH_SIZE_FIELD = Field(default=100000, description=BATCH_SIZE_DESCRIPTION)
DRY_RUN_FIELD = Field(default=False, description=DRY_RUN_DESCRIPTION)
SINCE_FIELD = Field(default=None, description=SINCE_DESCRIPTION)
CLEANUP_ORPHANS_FIELD = Field(default=True, description=CLEANUP_ORPHANS_DESCRIPTION)
CATALOGS_FIELD = Field(default=None, description=CATALOGS_DESCRIPTION)


def schedule_env_var(task_name: str) -> str:
    return f"TASK_SCHEDULE_{task_name.upper().replace('-', '_')}"


def cron_from_env(task_name: str, environ: Mapping[str, str] | None = None) -> str | None:
    env: Mapping[str, str] = os.environ if environ is None else environ
    value = env.get(schedule_env_var(task_name), "").strip()
    return value or None


def _prefect_message_renderer(_logger: object, _method_name: str, event_dict: MutableMapping[str, Any]) -> str:
    event = str(event_dict.pop("event", ""))
    parts = [event] if event else []
    for key, value in event_dict.items():
        parts.append(f"{key}={value}")
    return " ".join(parts)


def _flow_logger() -> structlog.stdlib.BoundLogger:
    log_level = os.getenv("LOG_LEVEL", "info")
    run_logger = get_run_logger()
    # Prefect's flow-run logger defaults above DEBUG; align it with LOG_LEVEL
    # so structlog.debug(...) actually reaches the UI.
    level = getattr(logging, log_level.upper(), logging.INFO)
    if isinstance(run_logger, logging.LoggerAdapter):
        run_logger.logger.setLevel(level)
    else:
        run_logger.setLevel(level)
    return structlog.wrap_logger(
        run_logger,
        processors=[
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _prefect_message_renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
    )


def run_task(
    task_name: str,
    batch_size: int = 100000,
    dry_run: bool = False,
    since: datetime.datetime | None = None,
    cleanup_orphans: bool = True,
    catalogs: Sequence[str] | None = None,
) -> None:
    log = _flow_logger()
    params: dict[str, Any] = {
        "batch_size": int(batch_size),
        "dry_run": bool(dry_run),
        "silent": True,
        "cleanup_orphans": bool(cleanup_orphans),
    }
    if since is not None:
        params["since"] = since
    if catalogs is not None:
        params["catalogs"] = list(catalogs)
    task = tasks.get_task(task_name, log, params)
    cfg = tasks.Config()
    task.prepare(cfg)
    try:
        task.run()
    finally:
        task.cleanup()


@flow(
    log_prints=False,
    name="Layer 2 import (all catalogs)",
    description="Aggregates designation, ICRS, redshift, and nature from layer 1 into layer 2.",
)
def layer2_import(
    batch_size: int = BATCH_SIZE_FIELD,
    dry_run: bool = DRY_RUN_FIELD,
    since: datetime.datetime | None = SINCE_FIELD,
    cleanup_orphans: bool = CLEANUP_ORPHANS_FIELD,
    catalogs: list[str] | None = CATALOGS_FIELD,
) -> None:
    run_task(
        "layer2-import",
        batch_size=batch_size,
        dry_run=dry_run,
        since=since,
        cleanup_orphans=cleanup_orphans,
        catalogs=catalogs,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — designation",
    description="Majority-vote designations from layer 1 into layer 2.",
)
def layer2_import_designation(
    batch_size: int = BATCH_SIZE_FIELD,
    dry_run: bool = DRY_RUN_FIELD,
    since: datetime.datetime | None = SINCE_FIELD,
    cleanup_orphans: bool = CLEANUP_ORPHANS_FIELD,
) -> None:
    run_task(
        "layer2-import-designation",
        batch_size=batch_size,
        dry_run=dry_run,
        since=since,
        cleanup_orphans=cleanup_orphans,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — ICRS",
    description="Mean ICRS coordinates from layer 1 into layer 2.",
)
def layer2_import_icrs(
    batch_size: int = BATCH_SIZE_FIELD,
    dry_run: bool = DRY_RUN_FIELD,
    since: datetime.datetime | None = SINCE_FIELD,
    cleanup_orphans: bool = CLEANUP_ORPHANS_FIELD,
) -> None:
    run_task(
        "layer2-import-icrs",
        batch_size=batch_size,
        dry_run=dry_run,
        since=since,
        cleanup_orphans=cleanup_orphans,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — redshift",
    description="Mean redshifts (cz) from layer 1 into layer 2.",
)
def layer2_import_redshift(
    batch_size: int = BATCH_SIZE_FIELD,
    dry_run: bool = DRY_RUN_FIELD,
    since: datetime.datetime | None = SINCE_FIELD,
    cleanup_orphans: bool = CLEANUP_ORPHANS_FIELD,
) -> None:
    run_task(
        "layer2-import-redshift",
        batch_size=batch_size,
        dry_run=dry_run,
        since=since,
        cleanup_orphans=cleanup_orphans,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — nature",
    description="Majority-vote object nature/type from layer 1 into layer 2.",
)
def layer2_import_nature(
    batch_size: int = BATCH_SIZE_FIELD,
    dry_run: bool = DRY_RUN_FIELD,
    since: datetime.datetime | None = SINCE_FIELD,
    cleanup_orphans: bool = CLEANUP_ORPHANS_FIELD,
) -> None:
    run_task(
        "layer2-import-nature",
        batch_size=batch_size,
        dry_run=dry_run,
        since=since,
        cleanup_orphans=cleanup_orphans,
    )


FLOWS_BY_NAME: dict[str, Flow] = {
    "layer2-import": layer2_import,
    "layer2-import-designation": layer2_import_designation,
    "layer2-import-icrs": layer2_import_icrs,
    "layer2-import-redshift": layer2_import_redshift,
    "layer2-import-nature": layer2_import_nature,
}


def build_deployments(environ: Mapping[str, str] | None = None) -> list[RunnerDeployment]:
    deployments: list[RunnerDeployment] = []
    for task_name in LAYER2_TASK_NAMES:
        flow_fn = FLOWS_BY_NAME[task_name]
        cron = cron_from_env(task_name, environ)
        if cron is None:
            deployments.append(flow_fn.to_deployment(name=task_name))
        else:
            deployments.append(flow_fn.to_deployment(name=task_name, cron=cron))
    return deployments
