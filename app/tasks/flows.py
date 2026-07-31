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
from pydantic import BaseModel, Field

from app import tasks

LAYER2_TASK_NAMES: tuple[str, ...] = (
    "layer2-import",
    "layer2-import-designation",
    "layer2-import-icrs",
    "layer2-import-redshift",
    "layer2-import-nature",
    "layer2-orphan-cleanup",
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
WRITE_ORPHANS_DESCRIPTION = (
    "If true, remove orphaned PGC objects from layer 2 tables. If false, only report how many orphans would be removed."
)


class Layer2CatalogTaskParams(BaseModel):
    batch_size: int = Field(default=100000, description=BATCH_SIZE_DESCRIPTION)
    dry_run: bool = Field(default=False, description=DRY_RUN_DESCRIPTION)
    since: datetime.datetime | None = Field(default=None, description=SINCE_DESCRIPTION)
    cleanup_orphans: bool = Field(default=True, description=CLEANUP_ORPHANS_DESCRIPTION)


class Layer2ImportParams(Layer2CatalogTaskParams):
    catalogs: list[str] | None = Field(default=None, description=CATALOGS_DESCRIPTION)


class Layer2OrphanCleanupParams(BaseModel):
    write: bool = Field(default=False, description=WRITE_ORPHANS_DESCRIPTION)


DEFAULT_LAYER2_CATALOG_TASK_PARAMS = Layer2CatalogTaskParams()
DEFAULT_LAYER2_IMPORT_PARAMS = Layer2ImportParams()
DEFAULT_LAYER2_ORPHAN_CLEANUP_PARAMS = Layer2OrphanCleanupParams()


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
def layer2_import(params: Layer2ImportParams = DEFAULT_LAYER2_IMPORT_PARAMS) -> None:
    run_task(
        "layer2-import",
        batch_size=params.batch_size,
        dry_run=params.dry_run,
        since=params.since,
        cleanup_orphans=params.cleanup_orphans,
        catalogs=params.catalogs,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — designation",
    description="Majority-vote designations from layer 1 into layer 2.",
)
def layer2_import_designation(
    params: Layer2CatalogTaskParams = DEFAULT_LAYER2_CATALOG_TASK_PARAMS,
) -> None:
    run_task(
        "layer2-import-designation",
        batch_size=params.batch_size,
        dry_run=params.dry_run,
        since=params.since,
        cleanup_orphans=params.cleanup_orphans,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — ICRS",
    description="Aggregates ICRS coordinates from layer 1 into layer 2.",
)
def layer2_import_icrs(params: Layer2CatalogTaskParams = DEFAULT_LAYER2_CATALOG_TASK_PARAMS) -> None:
    run_task(
        "layer2-import-icrs",
        batch_size=params.batch_size,
        dry_run=params.dry_run,
        since=params.since,
        cleanup_orphans=params.cleanup_orphans,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — redshift",
    description="Aggregates redshifts (cz) from layer 1 into layer 2.",
)
def layer2_import_redshift(
    params: Layer2CatalogTaskParams = DEFAULT_LAYER2_CATALOG_TASK_PARAMS,
) -> None:
    run_task(
        "layer2-import-redshift",
        batch_size=params.batch_size,
        dry_run=params.dry_run,
        since=params.since,
        cleanup_orphans=params.cleanup_orphans,
    )


@flow(
    log_prints=False,
    name="Layer 2 import — nature",
    description="Majority-vote object nature/type from layer 1 into layer 2.",
)
def layer2_import_nature(params: Layer2CatalogTaskParams = DEFAULT_LAYER2_CATALOG_TASK_PARAMS) -> None:
    run_task(
        "layer2-import-nature",
        batch_size=params.batch_size,
        dry_run=params.dry_run,
        since=params.since,
        cleanup_orphans=params.cleanup_orphans,
    )


@flow(
    log_prints=False,
    name="Layer 2 orphan cleanup",
    description="Find and optionally remove PGC objects left without corresponding layer 1 records.",
)
def layer2_orphan_cleanup(
    params: Layer2OrphanCleanupParams = DEFAULT_LAYER2_ORPHAN_CLEANUP_PARAMS,
) -> None:
    log = _flow_logger()
    task = tasks.get_task("layer2-orphan-cleanup", log, {"write": bool(params.write)})
    cfg = tasks.Config()
    task.prepare(cfg)
    try:
        task.run()
    finally:
        task.cleanup()


FLOWS_BY_NAME: dict[str, Flow] = {
    "layer2-import": layer2_import,
    "layer2-import-designation": layer2_import_designation,
    "layer2-import-icrs": layer2_import_icrs,
    "layer2-import-redshift": layer2_import_redshift,
    "layer2-import-nature": layer2_import_nature,
    "layer2-orphan-cleanup": layer2_orphan_cleanup,
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
