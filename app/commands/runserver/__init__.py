import logging

import aiohttp_swagger
from aiohttp import web
from aiohttp_apispec import setup_aiohttp_apispec

from app import server
from app.server import handlers


def start():
    app = web.Application(middlewares=[server.exception_middleware])
    logging.basicConfig(level=logging.DEBUG)
    app.router.add_route("GET", "/ping", server.json_wrapper(handlers.ping))
    app.router.add_route("POST", "/api/v1/admin/source", server.json_wrapper(handlers.create_source))
    setup_aiohttp_apispec(app=app, title="My Documentation", version="v1")
    aiohttp_swagger.setup_swagger(app, swagger_url="/api/docs", ui_version=3)

    web.run_app(app)
