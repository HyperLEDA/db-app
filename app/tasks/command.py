from typing import final

import anyio
import structlog
from prefect.client.orchestration import get_client
from prefect.client.schemas.actions import WorkPoolCreate
from prefect.deployments.runner import RunnerDeployment
from prefect_docker.worker import DockerWorker

from app.lib import commands, tracing
from app.lib.storage import enums, postgres
from app.tasks import flows, interface, repository, structured_upload


def _ensure_work_pool(worker: interface.WorkerConfig) -> None:
    with get_client(sync_client=True) as client:
        client.create_work_pool(
            WorkPoolCreate(
                name=worker.work_pool_name,
                type="docker",
                base_job_template=DockerWorker.get_default_base_job_template(),
                concurrency_limit=worker.work_pool_concurrency,
            ),
            overwrite=True,
        )


async def _run_worker(work_pool_name: str) -> None:
    async with DockerWorker(work_pool_name=work_pool_name) as worker:
        await worker.start()


def _apply_deployments(deployments: list[RunnerDeployment]) -> None:
    for deployment in deployments:
        deployment.apply()


@final
class TasksWorkerCommand(commands.Command):
    @classmethod
    def help(cls) -> str:
        return """
            Registers layer2 Prefect deployments on the Docker work pool
            and starts a worker. Schedules are read from TASK_SCHEDULE_*
            environment variables (cron expressions; empty or unset means
            manual runs only).
        """

    def prepare(self) -> None:
        cfg = interface.Config()
        postgres.apply(cfg.storage)
        self.worker = interface.WorkerConfig.from_env()
        tracing.setup_tracing("tasks", cfg.tracing)
        storage = postgres.PgStorage(cfg.storage, structlog.get_logger(), enums.PG_ENUM_REGISTRY)
        storage.connect()
        try:
            repo = repository.Repository(storage, structlog.get_logger())
            catalog_schemas = structured_upload.build_catalog_schemas(repo)
        finally:
            storage.disconnect()
        self.deployments = flows.build_deployments(
            worker=self.worker,
            catalog_schemas=catalog_schemas,
        )

    def run(self) -> None:
        _ensure_work_pool(self.worker)
        _apply_deployments(self.deployments)
        anyio.run(_run_worker, self.worker.work_pool_name)

    def cleanup(self) -> None:
        pass
