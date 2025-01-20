import json
import pathlib

from app.commands import get_mock_depot
from app.lib import commands
from app.lib.web import server
from app.presentation.server import handlers


class GenerateSpecCommand(commands.Command):
    def __init__(self, filename: str):
        self.filename = filename

    def prepare(self):
        pass

    def run(self):
        routes = []

        for handler in handlers.routes:
            routes.append(handler(get_mock_depot()))

        spec, _ = server.get_router(routes)

        output_file = pathlib.Path(self.filename)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(json.dumps(spec.to_dict(), indent=2))

    def cleanup(self):
        pass
