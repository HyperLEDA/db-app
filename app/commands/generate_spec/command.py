import json
import pathlib
from typing import final

import structlog
from fastapi.openapi import utils

from app.domain import adminapi as domain
from app.lib import commands
from app.lib.web import server
from app.presentation import adminapi as presentation


@final
class GenerateSpecCommand(commands.Command):
    """
    Generates OpenAPI spec of the admin API and writes it to a file. This command is used by
    the generator of the documentation to create the API docs page.
    """

    def __init__(self, filename: str):
        self.filename = filename

    def prepare(self):
        pass

    def run(self):
        app = presentation.Server(
            domain.get_mock_actions(),
            server.ServerConfig(port=80, host="localhost"),
            structlog.get_logger(),
        )

        spec = utils.get_openapi(
            title=app.app.title,
            version=app.app.version,
            openapi_version=app.app.openapi_version,
            description=app.app.description,
            routes=app.app.routes,
        )

        output_file = pathlib.Path(self.filename)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(json.dumps(spec, indent=2))

    def cleanup(self):
        pass
