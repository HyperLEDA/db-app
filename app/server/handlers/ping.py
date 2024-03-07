from aiohttp import web
from aiohttp_apispec import docs, response_schema

from app import server
from app.server.errors.apierror import APIError


@docs(summary="Test that service is up and running")
@response_schema(APIError(), 400)
async def ping(_: web.Request) -> server.ResponseType:
    return {
        "ping": "pong",
    }
