from aiohttp import web
import aiohttp_swagger
from app import server
from app.server import handlers


def start():
    app = web.Application(middlewares=[server.exception_middleware])
    app.router.add_route("GET", "/ping", server.json_wrapper(handlers.ping))
    app.router.add_route("POST", "/api/v1/admin/source", server.json_wrapper(handlers.create_source))
    aiohttp_swagger.setup_swagger(app, swagger_url="/api/docs", ui_version=3)

    web.run_app(app)
