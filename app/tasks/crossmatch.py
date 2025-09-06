from typing import final

import structlog

from app.tasks import interface
from plugins.loader import discover_matchers, discover_solvers


@final
class CrossmatchTask(interface.Task):
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name
        self.log = structlog.get_logger()

    @classmethod
    def name(cls) -> str:
        return "crossmatch"

    def prepare(self, config: interface.Config):
        self.log.info("Preparing crossmatch task", table_name=self.table_name)

        self.log.info("Loading cross-identification plugins")
        matchers = discover_matchers("plugins/matchers")
        solvers = discover_solvers("plugins/solvers")

        self.log.info("matchers", lst=matchers.keys())
        self.log.info("solvers", lst=solvers.keys())

    def run(self):
        self.log.info("Running crossmatch task", table_name=self.table_name)
        # Dummy implementation - just log and exit successfully

    def cleanup(self):
        self.log.info("Cleaning up crossmatch task", table_name=self.table_name)
