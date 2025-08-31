from pathlib import Path
from typing import final

import yaml

from app import tasks
from app.lib import commands


@final
class CrossmatchCommand(commands.Command):
    def __init__(self, table_name: str, config_path: str) -> None:
        self.table_name = table_name
        self.config_path = config_path

    @classmethod
    def help(cls) -> str:
        return "Executes crossmatch task for a specified table."

    def prepare(self):
        cfg = self._parse_config(self.config_path)
        self.task = tasks.get_task("crossmatch", {"table_name": self.table_name})
        self.task.prepare(cfg)

    def run(self):
        self.task.run()

    def cleanup(self):
        self.task.cleanup()

    def _parse_config(self, path: str) -> tasks.Config:
        data = yaml.safe_load(Path(path).read_text())
        return tasks.Config(**data)
