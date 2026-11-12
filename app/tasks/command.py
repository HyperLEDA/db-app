from typing import final

import structlog
from prefect import serve

from app.lib import commands, tracing
from app.lib.storage import enums, postgres
from app.tasks import flows, interface, repository, structured_upload


@final
class ServeTasksCommand(commands.Command):
    @classmethod
    def help(cls) -> str:
        return """
            Registers layer2 Prefect tasks and serves them.
            Schedules are read from TASK_SCHEDULE_* environment variables
            (cron expressions; empty or unset means manual runs only).
        """

    def prepare(self) -> None:
        cfg = interface.Config()
        tracing.setup_tracing("tasks", cfg.tracing)
        storage = postgres.PgStorage(cfg.storage, structlog.get_logger(), enums.PG_ENUM_REGISTRY)
        storage.connect()
        try:
            repo = repository.Repository(storage, structlog.get_logger())
            catalog_schemas = structured_upload.build_catalog_schemas(repo)
        finally:
            storage.disconnect()
        self.deployments = flows.build_deployments(catalog_schemas=catalog_schemas)

    def run(self) -> None:
        serve(*self.deployments)

    def cleanup(self) -> None:
        pass
