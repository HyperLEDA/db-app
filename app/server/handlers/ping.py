from aiohttp_apispec import docs
from app import server
from aiohttp import web


@docs(summary="Test that service is up and running.")
async def ping(_: web.Request) -> server.ResponseType:
    """
    ---
    description: Test that service is up and running.
    produces:
    - text/plain
    responses:
        "200":
            description: successful operation
        "405":
            description: invalid HTTP Method
    """
    return {
        "ping": "pong",
    }
