from typing import Any
from aiohttp import web
from aiohttp_apispec import docs


@docs(summary="Test that service is up and running")
async def ping(_: web.Request) -> dict[str, Any]:
    return {
        "ping": "pong",
    }
