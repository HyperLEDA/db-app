from app import server
from aiohttp import web


async def create_source(request: web.Request) -> server.ResponseType:
    request = await request.json()
    print(request)

    return {"data": {}}
