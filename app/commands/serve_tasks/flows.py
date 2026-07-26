import os
from collections.abc import Mapping

import structlog
from prefect import flow
from prefect.deployments.runner import RunnerDeployment
from prefect.flows import Flow

from app import tasks

LAYER2_TASK_NAMES: tuple[str, ...] = (
    "layer2-import",
    "layer2-import-designation",
    "layer2-import-icrs",
    "layer2-import-redshift",
    "layer2-import-nature",
)


def schedule_env_var(task_name: str) -> str:
    return f"TASK_SCHEDULE_{task_name.upper().replace('-', '_')}"


def cron_from_env(task_name: str, environ: Mapping[str, str] | None = None) -> str | None:
    env: Mapping[str, str] = os.environ if environ is None else environ
    value = env.get(schedule_env_var(task_name), "").strip()
    return value or None


def run_task(task_name: str, batch_size: int = 100000, dry_run: bool = False) -> None:
    log = structlog.get_logger()
    task = tasks.get_task(
        task_name,
        log,
        {
            "batch_size": int(batch_size),
            "dry_run": bool(dry_run),
            "silent": True,
        },
    )
    cfg = tasks.Config()
    task.prepare(cfg)
    try:
        task.run()
    finally:
        task.cleanup()


@flow(log_prints=True, name="layer2-import")
def layer2_import(batch_size: int = 100000, dry_run: bool = False) -> None:
    run_task("layer2-import", batch_size=batch_size, dry_run=dry_run)


@flow(log_prints=True, name="layer2-import-designation")
def layer2_import_designation(batch_size: int = 100000, dry_run: bool = False) -> None:
    run_task("layer2-import-designation", batch_size=batch_size, dry_run=dry_run)


@flow(log_prints=True, name="layer2-import-icrs")
def layer2_import_icrs(batch_size: int = 100000, dry_run: bool = False) -> None:
    run_task("layer2-import-icrs", batch_size=batch_size, dry_run=dry_run)


@flow(log_prints=True, name="layer2-import-redshift")
def layer2_import_redshift(batch_size: int = 100000, dry_run: bool = False) -> None:
    run_task("layer2-import-redshift", batch_size=batch_size, dry_run=dry_run)


@flow(log_prints=True, name="layer2-import-nature")
def layer2_import_nature(batch_size: int = 100000, dry_run: bool = False) -> None:
    run_task("layer2-import-nature", batch_size=batch_size, dry_run=dry_run)


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
