from marshmallow import ValidationError
from app import server
from aiohttp import web
from app.server.errors import new_validation_error

from app.server.schema import CreateSourceRequestSchema


async def create_source(request: web.Request) -> server.ResponseType:
    request = await request.json()

    schema = CreateSourceRequestSchema()
    try:
        schema.load(request)
    except ValidationError as e:
        raise new_validation_error(str(e))

    return {"data": {}}
