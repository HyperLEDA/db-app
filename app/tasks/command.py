from typing import final

from prefect import serve

from app.lib import commands
from app.tasks import flows


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
        self.deployments = flows.build_deployments()

    def run(self) -> None:
        serve(*self.deployments)

    def cleanup(self) -> None:
        pass
