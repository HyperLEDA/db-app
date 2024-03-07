from app import server
from aiohttp import web


async def ping(_: web.Request) -> server.ResponseType:
    """
    ---
    description: This end-point allow to test that service is up.
    tags:
    - Health check
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
