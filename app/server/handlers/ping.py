from app import server
from aiohttp import web


async def ping(_: web.Request) -> server.ResponseType:
    return {
        "ping": "pong",
    }
