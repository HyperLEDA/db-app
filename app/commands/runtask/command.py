import json
import logging
from pathlib import Path
from typing import Any, final

import structlog
import yaml

from app import tasks
from app.lib import commands


@final
class RunTaskCommand(commands.Command):
    def __init__(
        self,
        task_name: str,
        config_path: str,
        input_data_path: str | None = None,
        input_data: dict[str, Any] | None = None,
        task_args: tuple[str, ...] | None = None,
    ) -> None:
        if input_data is None:
            input_data = {}
        if task_args is None:
            task_args = ()

        self.task_name = task_name
        self.config_path = config_path
        self.input_data_path = input_data_path
        self.input_data = input_data
        self.task_args = task_args

    @classmethod
    def help(cls) -> str:
        return f"""
            Executes specified task.
            Possible tasks are: {", ".join(tasks.list_tasks())}.
        """

    def prepare(self):
        cfg = parse_config(self.config_path)

        input_data = self.input_data

        if self.input_data_path is not None:
            input_data.update(json.loads(Path(self.input_data_path).read_text()))

        task_args_dict = self._parse_task_args(self.task_args)
        input_data.update(task_args_dict)

        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        )
        logger = structlog.get_logger()

        self.task = tasks.get_task(self.task_name, logger, input_data)
        self.task.prepare(cfg)

    def run(self):
        self.task.run()

    def cleanup(self):
        self.task.cleanup()

    def _parse_task_args(self, task_args: tuple[str, ...]) -> dict[str, Any]:
        args_dict = {}

        i = 0
        while i < len(task_args):
            arg = task_args[i]

            if arg.startswith("--"):
                key = arg[2:].replace("-", "_")

                if i + 1 < len(task_args) and not task_args[i + 1].startswith("--"):
                    value = task_args[i + 1]
                    args_dict[key] = value
                    i += 2
                else:
                    args_dict[key] = True
                    i += 1
            else:
                i += 1

        return args_dict


def parse_config(path: str) -> tasks.Config:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Config file not found: '{path}'")

    data = yaml.safe_load(p.read_text())
    return tasks.Config(**data)
