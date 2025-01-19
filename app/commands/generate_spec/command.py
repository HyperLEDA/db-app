import json
import pathlib
import warnings

import apispec
from aiohttp import web
from apispec.ext import marshmallow as apimarshamllow
from apispec_webframeworks import aiohttp as apiaiohttp

from app.lib import commands
from app.lib.server import middleware
from app.presentation.server import handlers


class GenerateSpecCommand(commands.Command):
    def __init__(self, filename: str):
        self.filename = filename

    def prepare(self):
        pass

    def run(self):
        # silence warning from apispec since it is a desired behaviour in this case.
        warnings.filterwarnings("ignore", message="(.*?)has already been added to the spec(.*?)", module="apispec")

        app = web.Application(middlewares=[middleware.exception_middleware])

        spec = apispec.APISpec(
            title="HyperLeda API specification",
            version="1.0.0",
            openapi_version="3.0.2",
            plugins=[apimarshamllow.MarshmallowPlugin(), apiaiohttp.AiohttpPlugin()],
        )

        for route_description in handlers.routes:
            route = app.router.add_route(
                route_description.method.value,
                route_description.endpoint,
                route_description.handler,
            )

            if route_description.request_schema.__name__ not in spec.components.schemas:
                spec.components.schema(
                    route_description.request_schema.__name__, schema=route_description.request_schema
                )
            if route_description.response_schema.__name__ not in spec.components.schemas:
                spec.components.schema(
                    route_description.response_schema.__name__, schema=route_description.response_schema
                )

            spec.path(route=route)

        output_file = pathlib.Path(self.filename)
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(json.dumps(spec.to_dict(), indent=2))

    def cleanup(self):
        pass
