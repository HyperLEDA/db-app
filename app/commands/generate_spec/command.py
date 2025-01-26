import json
import pathlib
from typing import final

from app.commands.adminapi import depot
from app.lib import commands
from app.lib.web import server
from app.presentation import adminapi


@final
class GenerateSpecCommand(commands.Command):
    def __init__(self, filename: str):
        self.filename = filename

    def prepare(self):
        pass

    def run(self):
        routes = []

        for handler in adminapi.routes:
            routes.append(handler(depot.get_mock_depot()))

        spec, _ = server.get_router(routes)

        output_file = pathlib.Path(self.filename)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(json.dumps(spec.to_dict(), indent=2))

    def cleanup(self):
        pass
