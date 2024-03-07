from aiohttp import web

from app import server
from app.server import handlers


routes = [
    web.get("/ping", server.json_wrapper(handlers.ping)),
    web.post("/api/v1/admin/source", server.json_wrapper(handlers.create_source)),
]


def start():
    app = web.Application(middlewares=[server.exception_middleware])
    app.add_routes(routes)

    web.run_app(app)
