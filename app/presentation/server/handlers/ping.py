from typing import Any

from aiohttp import web
from aiohttp_apispec import docs

from app import domain


@docs(summary="Test that service is up and running")
async def ping(_: domain.Actions, __: web.Request) -> Any:
    return {
        "ping": "pong",
    }
