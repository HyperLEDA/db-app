import dataclasses
from typing import Any

from aiohttp import web
from aiohttp_apispec import docs, querystring_schema, response_schema
from marshmallow import ValidationError

from app.presentation import actions
from app.presentation.model import GetObjectRequestSchema, GetObjectResponseSchema
from app.presentation.server.exceptions.apiexception import new_validation_error


@docs(
    summary="Get information about the object",
    tags=["objects"],
    description="Retrieves information about the object using its id.",
)
@querystring_schema(GetObjectRequestSchema())
@response_schema(GetObjectResponseSchema(), 200)
async def get_object(r: web.Request) -> dict[str, Any]:
    try:
        request = GetObjectRequestSchema().load(r.rel_url.query)
    except ValidationError as e:
        raise new_validation_error(str(e))

    response = actions.get_object(request)

    return {"data": dataclasses.asdict(response)}
