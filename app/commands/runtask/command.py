import json
from pathlib import Path
from typing import final

from app import tasks
from app.commands.runtask import config
from app.lib import commands


@final
class RunTaskCommand(commands.Command):
    def __init__(self, task_name: str, config_path: str, input_data_path: str | None) -> None:
        self.task_name = task_name
        self.config_path = config_path
        self.input_data_path = input_data_path

    @classmethod
    def help(cls) -> str:
        return f"""
            Executes specified task. 
            Input should be specified as a separate file. 
            Possible tasks are: {", ".join(tasks.list_tasks())}.
        """

    def prepare(self):
        cfg = config.parse_config(self.config_path)

        input_data = {}

        if self.input_data_path is not None:
            input_data = json.loads(Path(self.input_data_path).read_text())

        self.task = tasks.get_task(self.task_name, input_data)
        self.task.prepare(cfg)

    def run(self):
        self.task.run()

    def cleanup(self):
        self.task.cleanup()
